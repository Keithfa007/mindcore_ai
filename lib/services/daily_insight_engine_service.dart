import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/env/env.dart';

class DailyInsightBundle {
  final String affirmation;
  final String tip;
  final String reflectionPrompt;
  final String summaryLine;

  const DailyInsightBundle({
    required this.affirmation,
    required this.tip,
    required this.reflectionPrompt,
    required this.summaryLine,
  });

  Map<String, dynamic> toJson() => {
        'affirmation': affirmation,
        'tip': tip,
        'reflectionPrompt': reflectionPrompt,
        'summaryLine': summaryLine,
      };

  factory DailyInsightBundle.fromJson(Map<String, dynamic> json) {
    String read(String key, String fallback) {
      final value = json[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
      return fallback;
    }

    return DailyInsightBundle(
      affirmation: read('affirmation', 'You are allowed to reset and begin again.'),
      tip: read('tip', 'Take one slow breath before your next task.'),
      reflectionPrompt: read('reflectionPrompt', 'What do I need most today?'),
      summaryLine: read('summaryLine', 'A softer pace still counts as progress.'),
    );
  }

  static const fallback = DailyInsightBundle(
    affirmation: 'You are allowed to reset and begin again.',
    tip: 'Take one slow breath before your next task.',
    reflectionPrompt: 'What do I need most today?',
    summaryLine: 'A softer pace still counts as progress.',
  );
}

class DailyInsightEngineService {
  DailyInsightEngineService._();

  static const String _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const String _model = 'gpt-4o-mini';
  static String get _apiKey => Env.openaiKey;

  // Cache key includes full date AND day name — guarantees refresh every day
  static String _cacheKey(DateTime now, String mood) {
    final date    = DateFormat('yyyy-MM-dd').format(now);
    final dayName = DateFormat('EEEE').format(now).toLowerCase(); // e.g. "monday"
    return 'daily_insight_bundle_v2_${date}_${dayName}_${mood.toLowerCase().trim()}';
  }

  // Day-of-week context injected into the AI prompt
  static String _dayContext(DateTime now) {
    final day  = DateFormat('EEEE').format(now);   // e.g. "Monday"
    final hour = now.hour;
    final timeOfDay = hour < 9
        ? 'early morning'
        : hour < 12
            ? 'morning'
            : hour < 17
                ? 'afternoon'
                : hour < 21
                    ? 'evening'
                    : 'late night';

    // Day-specific tone hints
    String dayHint;
    switch (day) {
      case 'Monday':
        dayHint = 'Monday — a fresh start. The tone should be gently energising and forward-looking.';
        break;
      case 'Tuesday':
        dayHint = 'Tuesday — into the week now. Encourage steadiness and momentum.';
        break;
      case 'Wednesday':
        dayHint = 'Wednesday — midweek. Acknowledge the effort so far and encourage continuing.';
        break;
      case 'Thursday':
        dayHint = 'Thursday — nearly there. A tone of quiet persistence and hope for the end of the week.';
        break;
      case 'Friday':
        dayHint = 'Friday — the week is ending. Reflect on what was achieved. Warmth and lightness.';
        break;
      case 'Saturday':
        dayHint = 'Saturday — the weekend. Rest, recovery, and doing things that restore energy.';
        break;
      case 'Sunday':
        dayHint = 'Sunday — a quieter day. Gentle reflection, preparing mentally for the week ahead.';
        break;
      default:
        dayHint = '$day — be present and warm.';
    }

    return 'Today is $day $timeOfDay. $dayHint';
  }

  static Future<DailyInsightBundle> getBundle({
    String moodLabel = 'calm',
    String contextSummary = '',
    bool forceRefresh = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final now   = DateTime.now();
    final key   = _cacheKey(now, moodLabel);

    // Return cached version if exists and not forcing refresh
    if (!forceRefresh) {
      final raw = prefs.getString(key);
      if (raw != null && raw.trim().isNotEmpty) {
        try {
          final parsed = jsonDecode(raw);
          if (parsed is Map<String, dynamic>) {
            return DailyInsightBundle.fromJson(parsed);
          }
        } catch (_) {}
      }
    }

    if (_apiKey.trim().isEmpty) {
      final bundle = DailyInsightBundle.fallback;
      await prefs.setString(key, jsonEncode(bundle.toJson()));
      return bundle;
    }

    try {
      final dayCtx = _dayContext(now);

      final response = await http.post(
        Uri.parse(_endpoint),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_apiKey',
        },
        body: jsonEncode({
          'model': _model,
          'temperature': 0.75,
          'messages': [
            {
              'role': 'system',
              'content': '''
You are MindCore AI's daily insight engine.
Generate a short, warm, personalised daily insight for a mental wellness app user.

$dayCtx
User mood: $moodLabel
${contextSummary.isNotEmpty ? 'Context: $contextSummary' : ''}

Return ONLY valid JSON with exactly these four keys:
- affirmation: one short, genuine affirmation (not cheesy). Max 15 words.
- tip: one practical mental wellness micro-tip relevant to the day and mood. Max 20 words.
- reflectionPrompt: one thoughtful reflection question for the user to sit with. Max 15 words.
- summaryLine: one poetic or grounding closing line. Max 12 words.

Rules:
- Never use toxic positivity ("You've got this!", "Everything happens for a reason!")
- The content must feel specific to $dayCtx — not generic
- Vary the content meaningfully from day to day
- Warm, human, real — not clinical or hollow
- Return JSON only. No markdown, no backticks, no extra text.
''',
            },
            {
              'role': 'user',
              'content': 'Generate today\'s insight.',
            },
          ],
        }),
      ).timeout(const Duration(seconds: 15));

      final body    = jsonDecode(response.body);
      final content = body['choices'][0]['message']['content'] as String;

      // Strip any accidental markdown fences
      final clean = content
          .replaceAll(RegExp(r'```json\s*'), '')
          .replaceAll(RegExp(r'```\s*'), '')
          .trim();

      final parsed = jsonDecode(clean);
      if (parsed is Map<String, dynamic>) {
        final bundle = DailyInsightBundle.fromJson(parsed);
        await prefs.setString(key, jsonEncode(bundle.toJson()));
        return bundle;
      }

      throw Exception('Unexpected response format');
    } catch (_) {
      final bundle = DailyInsightBundle.fallback;
      await prefs.setString(key, jsonEncode(bundle.toJson()));
      return bundle;
    }
  }

  // Removes today's cached insight so it regenerates fresh on next call
  static Future<void> invalidateToday({String? moodLabel}) async {
    final prefs = await SharedPreferences.getInstance();
    final now   = DateTime.now();

    if (moodLabel != null) {
      await prefs.remove(_cacheKey(now, moodLabel));
      return;
    }

    // Remove all today's insight keys (v1 and v2) for any mood
    final date    = DateFormat('yyyy-MM-dd').format(now);
    final toRemove = prefs.getKeys().where((k) =>
        k.contains('daily_insight_bundle_') && k.contains(date)).toList();
    for (final k in toRemove) {
      await prefs.remove(k);
    }
  }
}
