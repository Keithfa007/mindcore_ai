// lib/services/mindscore_service.dart
//
// MindScore — a single composite wellness number (0–100).
// Combines: mood (30%), habits (25%), journal (15%), chat (15%), streak (15%).
// Calculated on-the-fly from existing data sources.

import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/habit_service.dart';
import 'package:mindcore_ai/services/streak_service.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';

class MindScoreResult {
  final int score;           // 0–100
  final double moodScore;    // 0–100 (from latest mood 1-5)
  final double habitScore;   // 0–100 (% habits completed)
  final double journalScore; // 0 or 100
  final double chatScore;    // 0 or 100
  final double streakScore;  // 0–100 (caps at 7-day streak)
  final int streak;

  const MindScoreResult({
    required this.score,
    required this.moodScore,
    required this.habitScore,
    required this.journalScore,
    required this.chatScore,
    required this.streakScore,
    required this.streak,
  });

  static const empty = MindScoreResult(
    score: 0,
    moodScore: 0, habitScore: 0, journalScore: 0,
    chatScore: 0, streakScore: 0, streak: 0,
  );
}

class MindScoreService {
  MindScoreService._();

  // Weights
  static const _wMood    = 0.30;
  static const _wHabit   = 0.25;
  static const _wJournal = 0.15;
  static const _wChat    = 0.15;
  static const _wStreak  = 0.15;

  /// Calculate today's MindScore from all data sources.
  static Future<MindScoreResult> calculate() async {
    // ── 1. Mood (latest today, scaled 1-5 → 0-100) ──────────────
    double moodScore = 50; // default: neutral
    try {
      final entries = await MoodRepo.instance.fetchAll();
      final now = DateTime.now();
      final todayEntries = entries.where((e) =>
          e.timestamp.year == now.year &&
          e.timestamp.month == now.month &&
          e.timestamp.day == now.day);
      if (todayEntries.isNotEmpty) {
        final avg = todayEntries.map((e) => e.score).reduce((a, b) => a + b) /
            todayEntries.length;
        moodScore = ((avg - 1) / 4.0 * 100).clamp(0, 100);
      }
    } catch (_) {}

    // ── 2. Habits (% completed today) ────────────────────────────
    double habitScore = 0;
    try {
      final habits = await HabitService.getToday();
      habitScore = (habits.completionPercent * 100).clamp(0, 100);
    } catch (_) {}

    // ── 3. Journal (did they write today?) ───────────────────────
    double journalScore = 0;
    try {
      final entries = await JournalService.getEntries();
      final now = DateTime.now();
      final hasToday = entries.any((e) =>
          e.timestamp.year == now.year &&
          e.timestamp.month == now.month &&
          e.timestamp.day == now.day);
      journalScore = hasToday ? 100 : 0;
    } catch (_) {}

    // ── 4. Chat (did they chat today?) ───────────────────────────
    double chatScore = 0;
    try {
      final prefs = await SharedPreferences.getInstance();
      final keys = prefs.getKeys();
      final now = DateTime.now();
      final todayStr = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      // Check if any chat conversation was updated today
      for (final k in keys) {
        if (k.startsWith('chat_conversations_') && k != 'chat_conversations_index') {
          final raw = prefs.getString(k);
          if (raw != null && raw.contains(todayStr)) {
            chatScore = 100;
            break;
          }
        }
      }
    } catch (_) {}

    // ── 5. Streak (caps at 7 days for full score) ────────────────
    int streak = 0;
    double streakScore = 0;
    try {
      streak = await StreakService.currentStreak();
      streakScore = ((streak / 7.0) * 100).clamp(0, 100);
    } catch (_) {}

    // ── Composite ────────────────────────────────────────────────
    final raw = (moodScore * _wMood) +
        (habitScore * _wHabit) +
        (journalScore * _wJournal) +
        (chatScore * _wChat) +
        (streakScore * _wStreak);

    return MindScoreResult(
      score: raw.round().clamp(0, 100),
      moodScore: moodScore,
      habitScore: habitScore,
      journalScore: journalScore,
      chatScore: chatScore,
      streakScore: streakScore,
      streak: streak,
    );
  }

  /// Get the last 7 days of MindScore for trend display.
  /// This is an approximation — recalculates from available data.
  static Future<List<int>> weeklyTrend() async {
    final scores = <int>[];
    final now = DateTime.now();

    for (int i = 6; i >= 0; i--) {
      final date = now.subtract(Duration(days: i));
      double dayScore = 50; // default

      try {
        // Mood for that day
        final entries = await MoodRepo.instance.fetchAll();
        final dayEntries = entries.where((e) =>
            e.timestamp.year == date.year &&
            e.timestamp.month == date.month &&
            e.timestamp.day == date.day);
        double moodScore = 50;
        if (dayEntries.isNotEmpty) {
          final avg = dayEntries.map((e) => e.score).reduce((a, b) => a + b) /
              dayEntries.length;
          moodScore = ((avg - 1) / 4.0 * 100).clamp(0, 100);
        }

        // Habits for that day
        final dateKey = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
        double habitScore = 0;
        try {
          final history = await HabitService.getHistory(days: 7);
          final dayHabit = history.where((h) => h.date == dateKey);
          if (dayHabit.isNotEmpty) {
            habitScore = (dayHabit.first.completionPercent * 100).clamp(0, 100);
          }
        } catch (_) {}

        dayScore = (moodScore * 0.55) + (habitScore * 0.45);
      } catch (_) {}

      scores.add(dayScore.round().clamp(0, 100));
    }

    return scores;
  }
}
