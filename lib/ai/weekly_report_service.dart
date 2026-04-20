// lib/ai/weekly_report_service.dart
//
// Generates a personalised weekly mood report via OpenAI.
// Cached by the Monday of the current week (YYYY_MM_DD of Monday).
// Regenerates automatically every Monday when the user opens the app.

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/env/env.dart';

class WeeklyReport {
  final String summary;    // 1-2 sentence overall mood summary
  final String bestDay;    // e.g. "Thursday"
  final String highlight;  // what seemed to help
  final String watchOut;   // pattern to be aware of
  final DateTime generatedAt;

  const WeeklyReport({
    required this.summary,
    required this.bestDay,
    required this.highlight,
    required this.watchOut,
    required this.generatedAt,
  });

  Map<String, dynamic> toJson() => {
        'summary': summary,
        'bestDay': bestDay,
        'highlight': highlight,
        'watchOut': watchOut,
        'generatedAt': generatedAt.toIso8601String(),
      };

  factory WeeklyReport.fromJson(Map<String, dynamic> j) => WeeklyReport(
        summary: j['summary'] as String? ?? '',
        bestDay: j['bestDay'] as String? ?? '',
        highlight: j['highlight'] as String? ?? '',
        watchOut: j['watchOut'] as String? ?? '',
        generatedAt: DateTime.tryParse(
                j['generatedAt'] as String? ?? '') ??
            DateTime.now(),
      );
}

class WeeklyReportService {
  static const _cacheKey    = 'weekly_report_v1';
  static const _cacheWeekKey = 'weekly_report_week_v1';

  static WeeklyReport? _memCache;
  static String?       _memWeek;

  /// Returns the report for the current week.
  /// Generates a fresh one the first time it is called each week (keyed to Monday).
  /// Returns null if there is not enough data (< 3 days logged).
  static Future<WeeklyReport?> getReport() async {
    final weekKey = _weekKey();

    // In-memory cache hit
    if (_memCache != null && _memWeek == weekKey) return _memCache;

    // Disk cache hit
    final prefs     = await SharedPreferences.getInstance();
    final savedWeek = prefs.getString(_cacheWeekKey);
    final savedJson = prefs.getString(_cacheKey);
    if (savedWeek == weekKey && savedJson != null && savedJson.isNotEmpty) {
      try {
        final report = WeeklyReport.fromJson(
            jsonDecode(savedJson) as Map<String, dynamic>);
        _memCache = report;
        _memWeek  = weekKey;
        return report;
      } catch (_) {}
    }

    // Generate fresh report for this week
    final report = await _generate();
    if (report != null) {
      _memCache = report;
      _memWeek  = weekKey;
      await prefs.setString(_cacheKey,     jsonEncode(report.toJson()));
      await prefs.setString(_cacheWeekKey, weekKey);
    }
    return report;
  }

  // ── Internal ───────────────────────────────────────────────────────────────

  /// Cache key = the date of Monday of the current week (YYYY_MM_DD).
  /// This is simple, reliable, and resets every Monday regardless of locale.
  static String _weekKey() {
    final now    = DateTime.now();
    // weekday: 1=Monday … 7=Sunday. Subtract (weekday-1) days to get Monday.
    final monday = DateTime(now.year, now.month, now.day)
        .subtract(Duration(days: now.weekday - 1));
    return '${monday.year}_${monday.month.toString().padLeft(2, '0')}_'
        '${monday.day.toString().padLeft(2, '0')}';
  }

  static Future<WeeklyReport?> _generate() async {
    final apiKey = Env.openaiKey;
    if (apiKey.trim().isEmpty) return null;

    // Fetch last 7 days of mood logs
    final all   = await MoodRepo.instance.fetchAll();
    final now   = DateTime.now();
    final start = DateTime(now.year, now.month, now.day)
        .subtract(const Duration(days: 6));

    // Group by day name
    const dayNames = [
      '', 'Monday', 'Tuesday', 'Wednesday',
      'Thursday', 'Friday', 'Saturday', 'Sunday',
    ];
    final byDay = <String, List<int>>{};
    for (final e in all) {
      final d = DateTime(
          e.timestamp.year, e.timestamp.month, e.timestamp.day);
      if (d.isBefore(start)) continue;
      final key = dayNames[d.weekday];
      (byDay[key] ??= []).add(e.score);
    }

    if (byDay.length < 3) return null; // not enough data yet

    // Build readable data string
    final sb = StringBuffer();
    // Sort days in calendar order for the prompt
    final orderedDays = <String>[];
    for (int i = 1; i <= 7; i++) {
      if (byDay.containsKey(dayNames[i])) orderedDays.add(dayNames[i]);
    }
    for (final day in orderedDays) {
      final scores = byDay[day]!;
      final avg    = scores.reduce((a, b) => a + b) / scores.length;
      sb.writeln(
          '- $day: avg ${avg.toStringAsFixed(1)}/5 '
          '(${scores.length} log${scores.length > 1 ? 's' : ''})');
    }

    // Compute best day
    String bestDay  = orderedDays.first;
    double bestAvg  = 0;
    for (final day in orderedDays) {
      final scores = byDay[day]!;
      final avg    = scores.reduce((a, b) => a + b) / scores.length;
      if (avg > bestAvg) { bestAvg = avg; bestDay = day; }
    }

    // Overall average
    final allScores  = byDay.values.expand((v) => v).toList();
    final overallAvg = allScores.reduce((a, b) => a + b) / allScores.length;

    final prompt = '''
You are MindCore AI, a compassionate mental wellness companion.
Analyse this user's mood data from the past 7 days and generate a short weekly report.

MOOD DATA (scale 1-5, 5 = best):
${sb.toString()}
Overall average: ${overallAvg.toStringAsFixed(1)}/5
Best day this week: $bestDay

Respond ONLY with a valid JSON object with exactly these 4 keys:
{
  "summary": "1-2 sentence compassionate overview of the week",
  "bestDay": "$bestDay",
  "highlight": "1 sentence about what the data suggests helped or went well",
  "watchOut": "1 sentence gentle heads-up about a pattern to be aware of"
}

RULES:
- Be warm and personal, not clinical
- No asterisks, no markdown, no quotes inside the strings
- If mood was mostly good, be encouraging
- If mood was mostly low, be compassionate and supportive
- Output ONLY the JSON. Nothing else.''';

    try {
      final response = await http
          .post(
            Uri.parse('https://api.openai.com/v1/chat/completions'),
            headers: {
              'Authorization': 'Bearer $apiKey',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'model': 'gpt-4o-mini',
              'messages': [
                {'role': 'user', 'content': prompt}
              ],
              'temperature': 0.65,
              'max_tokens': 200,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) return null;

      final json    = jsonDecode(response.body) as Map<String, dynamic>;
      final choices = json['choices'] as List?;
      if (choices == null || choices.isEmpty) return null;

      final content = (choices.first as Map<String, dynamic>)['message']
              ?['content']
              ?.toString()
              .trim() ??
          '';
      if (content.isEmpty) return null;

      final cleaned = content
          .replaceAll('```json', '')
          .replaceAll('```', '')
          .trim();

      final parsed = jsonDecode(cleaned) as Map<String, dynamic>;
      return WeeklyReport(
        summary:     parsed['summary']?.toString() ?? '',
        bestDay:     parsed['bestDay']?.toString() ?? bestDay,
        highlight:   parsed['highlight']?.toString() ?? '',
        watchOut:    parsed['watchOut']?.toString() ?? '',
        generatedAt: DateTime.now(),
      );
    } catch (_) {
      return null;
    }
  }
}
