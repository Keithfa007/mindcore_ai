import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:mindcore_ai/ai/agent_context.dart';
import 'package:mindcore_ai/ai/agent_prompts.dart';
import 'package:mindcore_ai/ai/agent_router.dart';
import 'package:mindcore_ai/ai/agent_type.dart';
import 'package:mindcore_ai/ai/orchestrator_models.dart';
import 'package:mindcore_ai/env/env.dart';
import 'package:mindcore_ai/pages/helpers/chat_persona_prefs.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';

class ChatStreamService {
  static String get _apiKey => Env.openaiKey;
  static const String _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const String _model = 'gpt-4o-mini';

  static Future<OrchestratorReply> streamOrchestratedReply({
    required List<Map<String, String>> history,
    required String moodLabel,
    required String userInput,
    required Future<void> Function(String delta) onDelta,
    String screen = 'chat',
  }) async {
    final crisis = _crisisResponseIfNeeded(userInput);
    if (crisis != null) {
      await onDelta(_crisisText);
      return const OrchestratorReply(reply: _crisisText, agent: AgentType.reset, confidence: 0.99, supportModeLabel: 'Immediate Support', suggestedActions: [], ttsText: _crisisText);
    }

    if (_apiKey.trim().isEmpty) {
      const text = 'AI is not configured yet (missing OPENAI_API_KEY).';
      await onDelta(text);
      return const OrchestratorReply(reply: text, agent: AgentType.companion, confidence: 0.35, supportModeLabel: 'Calm Companion', suggestedActions: [], ttsText: text);
    }

    final personaProfile = await ChatPersonaPrefs.loadPersona();
    final journalSummary = await _recentJournalSummary();
    final context = AgentContext(userInput: userInput, moodLabel: moodLabel, screen: screen, recentHistory: history, recentJournalSummary: journalSummary, now: DateTime.now());
    final decision = AgentRouter.decide(context);
    final maxOut = _maxOutForAgent(decision.agent.key);
    final system = AgentPrompts.buildSystemPrompt(agent: decision.agent, context: context, personaProfileText: personaProfile.profileText);

    final normalizedHistory = history.map((m) => {'role': (m['role'] ?? 'user'), 'content': (m['content'] ?? '')}).where((m) => (m['content'] as String).trim().isNotEmpty).toList();
    final shouldAppendUser = normalizedHistory.isEmpty || normalizedHistory.last['role'] != 'user' || normalizedHistory.last['content'] != userInput;
    final messages = <Map<String, dynamic>>[
      {'role': 'system', 'content': system},
      ...normalizedHistory,
      if (shouldAppendUser) {'role': 'user', 'content': userInput},
    ];

    final client = http.Client();
    final buffer = StringBuffer();
    try {
      final request = http.Request('POST', Uri.parse(_endpoint));
      request.headers.addAll({'Authorization': 'Bearer $_apiKey', 'Content-Type': 'application/json'});
      request.body = jsonEncode({'model': _model, 'messages': messages, 'temperature': 0.55, 'max_tokens': maxOut, 'stream': true});

      final response = await client.send(request).timeout(const Duration(seconds: 25));
      if (response.statusCode != 200) {
        final body = await response.stream.bytesToString();
        final err = _extractOpenAiError(body);
        final text = 'AI request failed (${response.statusCode}). ${err ?? "Please try again."}';
        await onDelta(text);
        return OrchestratorReply(reply: text, agent: decision.agent, confidence: decision.confidence, supportModeLabel: decision.agent.supportModeLabel, suggestedActions: decision.actions, ttsText: text);
      }

      final lines = response.stream.transform(utf8.decoder).transform(const LineSplitter());
      await for (final raw in lines) {
        final line = raw.trim();
        if (!line.startsWith('data:')) continue;
        final data = line.substring(5).trim();
        if (data == '[DONE]') break;
        try {
          final json = jsonDecode(data) as Map<String, dynamic>;
          final choices = json['choices'] as List?;
          String delta = '';
          if (choices != null && choices.isNotEmpty) {
            final first = choices.first;
            if (first is Map<String, dynamic>) {
              final deltaMap = first['delta'];
              if (deltaMap is Map<String, dynamic>) {
                delta = deltaMap['content']?.toString() ?? '';
              }
            }
          }
          if (delta.isNotEmpty) {
            buffer.write(delta);
            await onDelta(delta);
          }
        } catch (_) {}
      }

      final clean = buffer.toString().trim().isEmpty ? 'I’m here with you. Can you tell me a little more about what’s going on?' : buffer.toString().trim();
      return OrchestratorReply(reply: clean, agent: decision.agent, confidence: decision.confidence, supportModeLabel: decision.agent.supportModeLabel, suggestedActions: decision.actions, ttsText: clean);
    } on TimeoutException {
      const text = 'The AI took too long to respond. Please try again.';
      await onDelta(text);
      return OrchestratorReply(reply: text, agent: decision.agent, confidence: decision.confidence, supportModeLabel: decision.agent.supportModeLabel, suggestedActions: decision.actions, ttsText: text);
    } catch (_) {
      const text = 'My connection dropped for a second. Let’s try again in a moment.';
      await onDelta(text);
      return OrchestratorReply(reply: text, agent: decision.agent, confidence: decision.confidence, supportModeLabel: decision.agent.supportModeLabel, suggestedActions: decision.actions, ttsText: text);
    } finally {
      client.close();
    }
  }

  static const String _crisisText = '''I’m really sorry you’re feeling this way. I can’t help with self-harm, but you do deserve support right now.

If you’re in immediate danger or might act on these feelings, call your local emergency number now.

If you can, reach out to someone you trust and stay with them.

If you’re in the U.S. or Canada, you can call or text 988 (Suicide & Crisis Lifeline).
If you’re in the U.K. & ROI, call Samaritans at 116 123.
If you’re in Australia, call Lifeline at 13 11 14.
If you’re in Malta, call Malta's National Mental Health Helpline at 1579.

If you tell me your country, I can show the right local support options.''';

  static String? _crisisResponseIfNeeded(String input) {
    final t = input.toLowerCase();
    const cues = ['kill myself', 'suicide', 'end my life', 'want to die', 'harm myself', 'self harm', 'self-harm'];
    if (cues.any(t.contains)) return _crisisText;
    return null;
  }

  static int _maxOutForAgent(String agent) {
    switch (agent) {
      case 'reset':
      case 'sleep':
        return 220;
      case 'journal_insight':
      case 'focus':
      case 'prep':
        return 260;
      case 'routine':
        return 230;
      case 'companion':
      default:
        return 240;
    }
  }

  static Future<String> _recentJournalSummary() async {
    try {
      final entries = await JournalService.getEntries();
      if (entries.isEmpty) return '';
      final latest = entries.take(2).map((e) => e.note.trim()).where((e) => e.isNotEmpty).toList();
      if (latest.isEmpty) return '';
      final joined = latest.join(' | ');
      return joined.length > 320 ? '${joined.substring(0, 320)}…' : joined;
    } catch (_) {
      return '';
    }
  }

  static String? _extractOpenAiError(String body) {
    try {
      final j = jsonDecode(body);
      final err = (j is Map) ? j['error'] : null;
      if (err is Map) {
        final msg = err['message']?.toString();
        final code = err['code']?.toString();
        if (msg != null && msg.trim().isNotEmpty) {
          return code == null ? msg : '$msg (code: $code)';
        }
      }
    } catch (_) {}
    return null;
  }
}
