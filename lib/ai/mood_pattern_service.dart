// lib/ai/mood_pattern_service.dart
//
// Pure Dart pattern detection — no AI calls, fast and offline.
// Analyses the user's mood history to surface actionable insights.

import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';

/// A detected mood pattern with a human-readable message and suggested action.
class MoodPrediction {
  final String headline;
  final String detail;
  final IconData icon;
  final Color accentColor;
  final String? actionLabel;
  final String? actionRoute;

  const MoodPrediction({
    required this.headline,
    required this.detail,
    required this.icon,
    required this.accentColor,
    this.actionLabel,
    this.actionRoute,
  });
}

class MoodPatternService {
  /// Analyses the last 28 days of mood entries and returns the most
  /// relevant prediction, or null if there is not enough data.
  static Future<MoodPrediction?> detect() async {
    final all = await MoodRepo.instance.fetchAll();
    if (all.length < 5) return null;

    final now = DateTime.now();
    final cutoff = now.subtract(const Duration(days: 28));
    final recent = all.where((e) => e.timestamp.isAfter(cutoff)).toList();
    if (recent.length < 5) return null;

    final declining = _checkDecliningStreak(recent);
    if (declining != null) return declining;

    final improving = _checkImprovingStreak(recent);
    if (improving != null) return improving;

    final dow = _checkDayOfWeekPattern(recent);
    if (dow != null) return dow;

    final morning = _checkMorningPattern(recent);
    if (morning != null) return morning;

    return null;
  }

  // ── Pattern detectors ──────────────────────────────────────────────────

  static MoodPrediction? _checkDecliningStreak(List<MoodEntry> entries) {
    final byDay = <String, List<int>>{};
    for (final e in entries) {
      (byDay[_dayKey(e.timestamp)] ??= []).add(e.score);
    }
    final days = byDay.keys.toList()..sort();
    if (days.length < 4) return null;

    final lastFour = days.reversed.take(4).toList().reversed.toList();
    final avgs = lastFour
        .map((k) => byDay[k]!.reduce((a, b) => a + b) / byDay[k]!.length)
        .toList();

    bool declining = true;
    for (int i = 1; i < avgs.length; i++) {
      if (avgs[i] >= avgs[i - 1]) { declining = false; break; }
    }
    if (!declining || avgs.last > 3.0) return null;

    return const MoodPrediction(
      headline: 'Your mood has been dipping',
      detail:
          'The last few days have trended downward. A short reset or breathing session might help you level out.',
      icon: Icons.trending_down_rounded,
      accentColor: Color(0xFF9B7FFF),
      actionLabel: 'Try a reset',
      actionRoute: '/reset',
    );
  }

  static MoodPrediction? _checkImprovingStreak(List<MoodEntry> entries) {
    final byDay = <String, List<int>>{};
    for (final e in entries) {
      (byDay[_dayKey(e.timestamp)] ??= []).add(e.score);
    }
    final days = byDay.keys.toList()..sort();
    if (days.length < 4) return null;

    final lastFour = days.reversed.take(4).toList().reversed.toList();
    final avgs = lastFour
        .map((k) => byDay[k]!.reduce((a, b) => a + b) / byDay[k]!.length)
        .toList();

    bool improving = true;
    for (int i = 1; i < avgs.length; i++) {
      if (avgs[i] <= avgs[i - 1]) { improving = false; break; }
    }
    if (!improving || avgs.last < 3.5) return null;

    return const MoodPrediction(
      headline: 'You\'re on an upward streak',
      detail:
          'Your mood has improved steadily over the last few days. Keep building on what\'s working.',
      icon: Icons.trending_up_rounded,
      accentColor: Color(0xFF32D0BE),
      actionLabel: 'Log today',
      actionRoute: '/daily-hub',
    );
  }

  static MoodPrediction? _checkDayOfWeekPattern(List<MoodEntry> entries) {
    if (entries.length < 10) return null;

    final scores = <int, List<int>>{};
    for (final e in entries) {
      (scores[e.timestamp.weekday] ??= []).add(e.score);
    }
    if (scores.keys.length < 4) return null;

    final allScores = entries.map((e) => e.score).toList();
    final overall = allScores.reduce((a, b) => a + b) / allScores.length;

    int? lowestDow;
    double lowestAvg = double.infinity;
    for (final entry in scores.entries) {
      if (entry.value.length < 2) continue;
      final avg = entry.value.reduce((a, b) => a + b) / entry.value.length;
      if (avg < lowestAvg) { lowestAvg = avg; lowestDow = entry.key; }
    }
    if (lowestDow == null || overall - lowestAvg < 0.6) return null;

    const dayNames = [
      '', 'Mondays', 'Tuesdays', 'Wednesdays',
      'Thursdays', 'Fridays', 'Saturdays', 'Sundays',
    ];
    final dayName = dayNames[lowestDow];

    return MoodPrediction(
      headline: '$dayName tend to feel heavier',
      detail:
          'Based on your history, $dayName are often a lower point. A proactive session before the day starts can help.',
      icon: Icons.calendar_today_rounded,
      accentColor: const Color(0xFF4D7CFF),
      actionLabel: 'Open breathing',
      actionRoute: '/breathe',
    );
  }

  static MoodPrediction? _checkMorningPattern(List<MoodEntry> entries) {
    final morning = entries.where((e) => e.timestamp.hour < 10).toList();
    final rest   = entries.where((e) => e.timestamp.hour >= 10).toList();
    if (morning.length < 3 || rest.length < 3) return null;

    final morningAvg =
        morning.map((e) => e.score).reduce((a, b) => a + b) / morning.length;
    final restAvg =
        rest.map((e) => e.score).reduce((a, b) => a + b) / rest.length;
    if (restAvg - morningAvg < 0.8) return null;

    return const MoodPrediction(
      headline: 'Your mornings tend to start slow',
      detail:
          'Your mood before 10am is consistently lower than later in the day. A gentle morning routine could help.',
      icon: Icons.wb_twilight_rounded,
      accentColor: Color(0xFF74C3FF),
      actionLabel: 'Morning reset',
      actionRoute: '/reset',
    );
  }

  static String _dayKey(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
