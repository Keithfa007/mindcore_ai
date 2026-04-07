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
  static String get _apiKey  => Env.openaiKey;
  static const _endpoint    = 'https://api.openai.com/v1/chat/completions';
  static const _model       = 'gpt-4o-mini';
  // Slightly lower temperature — more consistent, grounded, less drift
  static const _temperature = 0.45;

  static Future<OrchestratorReply> streamOrchestratedReply({
    required List<Map<String, String>> history,
    required String moodLabel,
    required String userInput,
    required Future<void> Function(String delta) onDelta,
    String screen = 'chat',
  }) async {
    // ── Crisis gate ────────────────────────────────────────────────────
    if (_isCrisis(userInput)) {
      await onDelta(_crisisText);
      return const OrchestratorReply(
        reply:            _crisisText,
        agent:            AgentType.reset,
        confidence:       0.99,
        supportModeLabel: 'Immediate Support',
        suggestedActions: [],
        ttsText:          _crisisText,
      );
    }

    // ── API key guard ─────────────────────────────────────────────────
    if (_apiKey.trim().isEmpty) {
      const text = 'AI is not configured yet (missing API key).';
      await onDelta(text);
      return OrchestratorReply(
        reply: text, agent: AgentType.companion, confidence: 0.35,
        supportModeLabel: 'Calm Companion', suggestedActions: [], ttsText: text,
      );
    }

    // ── Build context ────────────────────────────────────────────────
    final personaProfile  = await ChatPersonaPrefs.loadPersona();
    final journalSummary  = await _recentJournalSummary();
    final context = AgentContext(
      userInput:            userInput,
      moodLabel:            moodLabel,
      screen:               screen,
      recentHistory:        history,
      recentJournalSummary: journalSummary,
      now:                  DateTime.now(),
    );
    final decision = AgentRouter.decide(context);
    final maxOut   = _maxTokensForAgent(decision.agent.key);
    final system   = AgentPrompts.buildSystemPrompt(
      agent:             decision.agent,
      context:           context,
      personaProfileText: personaProfile.profileText,
    );

    final normalizedHistory = history
        .map((m) => {'role': m['role'] ?? 'user', 'content': m['content'] ?? ''})
        .where((m) => (m['content'] as String).trim().isNotEmpty)
        .toList();
    final shouldAppendUser = normalizedHistory.isEmpty ||
        normalizedHistory.last['role'] != 'user' ||
        normalizedHistory.last['content'] != userInput;

    final messages = <Map<String, dynamic>>[
      {'role': 'system', 'content': system},
      ...normalizedHistory,
      if (shouldAppendUser) {'role': 'user', 'content': userInput},
    ];

    // ── Stream ───────────────────────────────────────────────────────────────
    final client = http.Client();
    final buffer = StringBuffer();
    try {
      final request = http.Request('POST', Uri.parse(_endpoint));
      request.headers.addAll({
        'Authorization': 'Bearer $_apiKey',
        'Content-Type':  'application/json',
      });
      request.body = jsonEncode({
        'model':       _model,
        'messages':    messages,
        'temperature': _temperature,
        'max_tokens':  maxOut,
        'stream':      true,
      });

      final response = await client
          .send(request)
          .timeout(const Duration(seconds: 28));

      if (response.statusCode != 200) {
        final body = await response.stream.bytesToString();
        final err  = _extractOpenAiError(body);
        final text = 'Something went wrong (${response.statusCode}). '
            '${err ?? "Please try again in a moment."}';
        await onDelta(text);
        return OrchestratorReply(
          reply: text, agent: decision.agent,
          confidence: decision.confidence,
          supportModeLabel: decision.agent.supportModeLabel,
          suggestedActions: decision.actions, ttsText: text,
        );
      }

      final lines = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final raw in lines) {
        final line = raw.trim();
        if (!line.startsWith('data:')) continue;
        final data = line.substring(5).trim();
        if (data == '[DONE]') break;
        try {
          final json    = jsonDecode(data) as Map<String, dynamic>;
          final choices = json['choices'] as List?;
          if (choices == null || choices.isEmpty) continue;
          final first    = choices.first;
          if (first is! Map<String, dynamic>) continue;
          final deltaMap = first['delta'];
          if (deltaMap is! Map<String, dynamic>) continue;
          final delta = deltaMap['content']?.toString() ?? '';
          if (delta.isNotEmpty) {
            buffer.write(delta);
            await onDelta(delta);
          }
        } catch (_) {}
      }

      final clean = buffer.toString().trim().isEmpty
          ? "I’m here with you. What’s going on?"
          : buffer.toString().trim();

      return OrchestratorReply(
        reply:            clean,
        agent:            decision.agent,
        confidence:       decision.confidence,
        supportModeLabel: decision.agent.supportModeLabel,
        suggestedActions: decision.actions,
        ttsText:          clean,
      );
    } on TimeoutException {
      const text = 'The response took too long. Please try again.';
      await onDelta(text);
      return OrchestratorReply(
        reply: text, agent: decision.agent, confidence: decision.confidence,
        supportModeLabel: decision.agent.supportModeLabel,
        suggestedActions: decision.actions, ttsText: text,
      );
    } catch (_) {
      const text = 'My connection dropped for a moment. Let’s try again.';
      await onDelta(text);
      return OrchestratorReply(
        reply: text, agent: decision.agent, confidence: decision.confidence,
        supportModeLabel: decision.agent.supportModeLabel,
        suggestedActions: decision.actions, ttsText: text,
      );
    } finally {
      client.close();
    }
  }

  // ── Crisis ───────────────────────────────────────────────────────────────

  static const String _crisisText =
      "What you\'re feeling right now matters, and so do you.\n\n"
      "I\'m not able to provide crisis support, but real help is available right now.\n\n"
      "\u{1F1F2}\u{1F1F9} Malta: 1579 (Mental Health Helpline) or 112 (Emergency)\n"
      "\u{1F1FA}\u{1F1F8} USA / Canada: Call or text 988 (Suicide & Crisis Lifeline)\n"
      "\u{1F1EC}\u{1F1E7} UK: Samaritans 116 123 (free, 24\/7)\n"
      "\u{1F1E6}\u{1F1FA} Australia: Lifeline 13 11 14\n"
      "\u{1F310} Everywhere: findahelpline.com\n\n"
      "If you are in immediate danger, please call emergency services now.\n\n"
      "You don\'t have to go through this alone. Someone is there.";

  // Expanded keyword list including indirect expressions people actually use
  static bool _isCrisis(String input) {
    final t = input.toLowerCase();
    const keywords = [
      'kill myself',
      'killing myself',
      'suicide',
      'suicidal',
      'end my life',
      'end it all',
      'take my life',
      'want to die',
      'wish i was dead',
      'better off dead',
      'not want to be here',
      "don't want to be here",
      'no reason to live',
      'harm myself',
      'self harm',
      'self-harm',
      'cut myself',
      'hurt myself',
      'everyone would be better off without me',
      'nobody would miss me',
      'can\'t go on',
      'cannot go on',
      'done with everything',
      'done with life',
    ];
    return keywords.any(t.contains);
  }

  // ── Token limits per agent ────────────────────────────────────────────────

  static int _maxTokensForAgent(String agent) {
    switch (agent) {
      case 'reset':           return 280;  // grounding needs space
      case 'sleep':           return 260;
      case 'journalInsight':  return 320;  // reflective mode needs room
      case 'focus':           return 300;
      case 'prep':            return 300;
      case 'routine':         return 280;
      case 'companion':
      default:                return 300;  // up from 240 — less rushed
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  static Future<String> _recentJournalSummary() async {
    try {
      final entries = await JournalService.getEntries();
      if (entries.isEmpty) return '';
      final latest = entries
          .take(3)
          .map((e) => e.note.trim())
          .where((e) => e.isNotEmpty)
          .toList();
      if (latest.isEmpty) return '';
      final joined = latest.join(' | ');
      return joined.length > 400
          ? '${joined.substring(0, 400)}…'
          : joined;
    } catch (_) {
      return '';
    }
  }

  static String? _extractOpenAiError(String body) {
    try {
      final j   = jsonDecode(body);
      final err = (j is Map) ? j['error'] : null;
      if (err is Map) {
        final msg  = err['message']?.toString();
        final code = err['code']?.toString();
        if (msg != null && msg.trim().isNotEmpty) {
          return code == null ? msg : '$msg (code: $code)';
        }
      }
    } catch (_) {}
    return null;
  }
}
