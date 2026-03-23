// lib/services/journal_reflection_service.dart
import 'dart:convert';
import 'dart:async';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/env/env.dart';

class JournalReflectionService {
  JournalReflectionService._();
  static final instance = JournalReflectionService._();

  static String get _apiKey => Env.openaiKey;

  static const String _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const String _model = 'gpt-4o-mini';

  static String _cacheKey(String entryId) => 'jr_reflect_$entryId';

  Future<String?> getCached(String entryId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_cacheKey(entryId));
    if (raw == null || raw.isEmpty) return null;
    return raw;
  }

  Future<void> setCached(String entryId, String text) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_cacheKey(entryId), text.trim());
  }

  Future<String> reflect({
    required String entryId,
    required String note,
    String moodLabel = 'Neutral',
    bool forceRefresh = false,
  }) async {
    if (_apiKey.trim().isEmpty) {
      return 'AI is not configured yet (missing OPENAI_API_KEY).';
    }

    if (note.trim().isEmpty) {
      return 'Write a little something first, then I can reflect with you.';
    }

    if (!forceRefresh) {
      final cached = await getCached(entryId);
      if (cached != null && cached.trim().isNotEmpty) return cached.trim();
    }

    final system = '''
You are MindCore AI — a warm, coach-like therapeutic companion.
Create a SHORT reflection on the journal entry.

Rules:
- Be positive but not toxic.
- Validate feelings in 1–2 lines.
- Offer 1 gentle reframe (realistic, hopeful).
- Offer 1 micro-step (2–10 minutes).
- End with ONE supportive question.
- No diagnosis, no medical/legal claims.
Output 120–180 words max.
Mood label: "$moodLabel"
''';

    final messages = [
      {'role': 'system', 'content': system},
      {'role': 'user', 'content': 'Journal entry:\n$note'},
    ];

    try {
      final res = await http
          .post(
        Uri.parse(_endpoint),
        headers: {
          'Authorization': 'Bearer $_apiKey',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'model': _model,
          'messages': messages,
          'temperature': 0.7,
          'max_tokens': 260,
        }),
      )
          .timeout(const Duration(seconds: 25));

      if (res.statusCode != 200) {
        final err = _extractOpenAiError(res.body);
        return 'Reflection failed (${res.statusCode}). ${err ?? "Try again in a moment."}';
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final text = (data['choices'] as List?)?.first?['message']?['content'] as String?;
      final out = (text ?? '').trim();

      if (out.isEmpty) {
        return 'I’m here with you. Want to tell me what part of the entry feels heaviest right now?';
      }

      await setCached(entryId, out);
      return out;
    } on TimeoutException {
      return 'The reflection took too long. Please try again.';
    } catch (_) {
      return 'I couldn’t generate a reflection just now. Try again in a moment.';
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
