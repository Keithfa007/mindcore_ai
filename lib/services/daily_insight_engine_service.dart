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

  static String _dayKey(DateTime now) => DateFormat('yyyy-MM-dd').format(now);

  static Future<DailyInsightBundle> getBundle({
    String moodLabel = 'calm',
    String contextSummary = '',
    bool forceRefresh = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final today = _dayKey(DateTime.now());
    final cacheKey = 'daily_insight_bundle_v1_${today}_${moodLabel.toLowerCase().trim()}';

    if (!forceRefresh) {
      final raw = prefs.getString(cacheKey);
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
      final fallback = DailyInsightBundle.fallback;
      await prefs.setString(cacheKey, jsonEncode(fallback.toJson()));
      return fallback;
    }

    try {
      final response = await http.post(
        Uri.parse(_endpoint),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_apiKey',
        },
        body: jsonEncode({
          'model': _model,
          'messages': [
            {
              'role': 'system',
              'content': 'Return JSON: affirmation, tip, reflectionPrompt, summaryLine.'
            },
            {
              'role': 'user',
              'content': 'Mood: $moodLabel | Context: $contextSummary'
            },
          ],
        }),
      );

      final body = jsonDecode(response.body);
      final content = body['choices'][0]['message']['content'];

      final parsed = jsonDecode(content);
      return DailyInsightBundle.fromJson(parsed);
    } catch (_) {
      final fallback = DailyInsightBundle.fallback;
      await prefs.setString(cacheKey, jsonEncode(fallback.toJson()));
      return fallback;
    }
  }

  static Future<void> invalidateToday({String? moodLabel}) async {
    final prefs = await SharedPreferences.getInstance();
    final today = _dayKey(DateTime.now());

    if (moodLabel != null) {
      await prefs.remove('daily_insight_bundle_v1_${today}_${moodLabel.toLowerCase().trim()}');
      return;
    }

    final keys = prefs.getKeys().where((k) => k.startsWith('daily_insight_bundle_v1_${today}_')).toList();
    for (final key in keys) {
      await prefs.remove(key);
    }
  }
}
