// lib/services/journey_service.dart
//
// Provides all data for the Journey screen and evolved home insight card.
// Reads from existing MoodRepo and StreakService — no new storage needed.

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/streak_service.dart';
import 'package:mindcore_ai/env/env.dart';
import 'package:http/http.dart' as http;

class WeeklyStats {
  final double thisWeekAvg;    // 1.0–5.0, 0 = no data
  final double lastWeekAvg;    // 1.0–5.0, 0 = no data
  final int    checkInsThisWeek;
  final int    streak;
  final String trendEmoji;     // ⬆️ ⬇️ →
  final String trendLabel;     // e.g. "up from 4.1 → 6.2"

  const WeeklyStats({
    required this.thisWeekAvg,
    required this.lastWeekAvg,
    required this.checkInsThisWeek,
    required this.streak,
    required this.trendEmoji,
    required this.trendLabel,
  });
}

class MonthlyTrend {
  /// 4 values — one per week (oldest → newest), normalised 0–1.
  final List<double> weeks;
  final String       monthLabel; // e.g. "May 2026"
  const MonthlyTrend({required this.weeks, required this.monthLabel});
}

class Milestone {
  final String emoji;
  final String title;
  final String subtitle;
  const Milestone({required this.emoji, required this.title, required this.subtitle});
}

class JourneyService {
  JourneyService._();

  static const _kInsightCache    = 'journey_insight_cache_v1';
  static const _kInsightCacheTs  = 'journey_insight_cache_ts_v1';
  static const _cacheDuration    = Duration(days: 7);

  // ── Weekly stats ─────────────────────────────────────────────────────────────

  static Future<WeeklyStats> getWeeklyStats() async {
    final all    = await MoodRepo.instance.fetchAll();
    final streak = await StreakService.currentStreak();
    final now    = DateTime.now();

    final thisWeekStart = now.subtract(Duration(days: 7));
    final lastWeekStart = now.subtract(Duration(days: 14));

    final thisWeek = all.where((e) => e.timestamp.isAfter(thisWeekStart)).toList();
    final lastWeek = all.where((e) =>
        e.timestamp.isAfter(lastWeekStart) &&
        e.timestamp.isBefore(thisWeekStart)).toList();

    final thisAvg = thisWeek.isEmpty
        ? 0.0
        : thisWeek.map((e) => e.score.toDouble()).reduce((a, b) => a + b) /
          thisWeek.length;
    final lastAvg = lastWeek.isEmpty
        ? 0.0
        : lastWeek.map((e) => e.score.toDouble()).reduce((a, b) => a + b) /
          lastWeek.length;

    String trendEmoji = '→';
    String trendLabel = 'Steady';

    if (thisAvg > 0 && lastAvg > 0) {
      final diff = thisAvg - lastAvg;
      if (diff > 0.2) {
        trendEmoji = '⬆️';
        trendLabel  = 'up from ${lastAvg.toStringAsFixed(1)} → ${thisAvg.toStringAsFixed(1)}';
      } else if (diff < -0.2) {
        trendEmoji = '⬇️';
        trendLabel  = 'down from ${lastAvg.toStringAsFixed(1)} → ${thisAvg.toStringAsFixed(1)}';
      } else {
        trendEmoji = '→';
        trendLabel  = 'steady at ${thisAvg.toStringAsFixed(1)}';
      }
    } else if (thisAvg > 0) {
      trendLabel = 'avg ${thisAvg.toStringAsFixed(1)} this week';
    }

    return WeeklyStats(
      thisWeekAvg:       thisAvg,
      lastWeekAvg:       lastAvg,
      checkInsThisWeek:  thisWeek.length,
      streak:            streak,
      trendEmoji:        trendEmoji,
      trendLabel:        trendLabel,
    );
  }

  // ── Monthly trend (4 weeks) ───────────────────────────────────────────────

  static Future<MonthlyTrend> getMonthlyTrend() async {
    final all = await MoodRepo.instance.fetchAll();
    final now = DateTime.now();
    final weeks = <double>[];

    for (int w = 3; w >= 0; w--) {
      final end   = now.subtract(Duration(days: w * 7));
      final start = end.subtract(const Duration(days: 7));
      final slice = all.where(
          (e) => e.timestamp.isAfter(start) && e.timestamp.isBefore(end));
      if (slice.isEmpty) {
        weeks.add(0.0);
      } else {
        final avg = slice.map((e) => e.score.toDouble()).reduce((a, b) => a + b) /
            slice.length;
        weeks.add((avg / 5.0).clamp(0.0, 1.0));
      }
    }

    final monthLabel =
        '${_monthName(now.month)} ${now.year}';

    return MonthlyTrend(weeks: weeks, monthLabel: monthLabel);
  }

  // ── Milestones ───────────────────────────────────────────────────────────────

  static Future<List<Milestone>> getMilestones() async {
    final all    = await MoodRepo.instance.fetchAll();
    final streak = await StreakService.currentStreak();
    final milestones = <Milestone>[];

    // Total check-ins
    final total = all.length;
    if (total >= 1)  milestones.add(const Milestone(emoji: '🌱', title: 'First check-in',       subtitle: 'You showed up. That matters.'));
    if (total >= 7)  milestones.add(const Milestone(emoji: '✨',     title: '7 check-ins',          subtitle: 'A week of showing up.'));
    if (total >= 30) milestones.add(const Milestone(emoji: '💫',     title: '30 check-ins',         subtitle: 'You are building something real.'));
    if (total >= 100)milestones.add(const Milestone(emoji: '🔥',     title: '100 check-ins',        subtitle: 'A hundred moments of honesty.'));

    // Streak milestones
    if (streak >= 3)  milestones.add(const Milestone(emoji: '💪',    title: '3-day streak',         subtitle: 'Three days in a row. Keep going.'));
    if (streak >= 7)  milestones.add(const Milestone(emoji: '🌟',    title: '7-day streak',         subtitle: 'A full week. That\'s consistency.'));
    if (streak >= 14) milestones.add(const Milestone(emoji: '🎉',    title: '2-week streak',        subtitle: 'Two weeks of showing up every day.'));
    if (streak >= 30) milestones.add(const Milestone(emoji: '🏆',    title: '30-day streak',        subtitle: 'A month. This is a real habit now.'));

    // Average mood milestones
    if (all.length >= 5) {
      final avg = all.take(10).map((e) => e.score.toDouble()).reduce((a, b) => a + b) /
          (all.length > 10 ? 10 : all.length);
      if (avg >= 3.5) milestones.add(const Milestone(emoji: '💚', title: 'Mood trending up',   subtitle: 'Your recent average is above 3.5 out of 5.'));
      if (avg >= 4.0) milestones.add(const Milestone(emoji: '💙', title: 'Consistently well', subtitle: 'Your recent average is above 4.0. Keep going.'));
    }

    return milestones;
  }

  // ── AI weekly insight paragraph ───────────────────────────────────────────────
  // Cached for 7 days. Generates one warm paragraph from real mood data.

  static Future<String> getWeeklyInsight(WeeklyStats stats) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedTs = prefs.getInt(_kInsightCacheTs) ?? 0;
      final cacheAge = DateTime.now().millisecondsSinceEpoch - cachedTs;

      if (cacheAge < _cacheDuration.inMilliseconds) {
        final cached = prefs.getString(_kInsightCache) ?? '';
        if (cached.isNotEmpty) return cached;
      }

      final apiKey = Env.openaiKey;
      if (apiKey.isEmpty) return '';

      final prompt = _buildInsightPrompt(stats);
      final res = await http.post(
        Uri.parse('https://api.openai.com/v1/chat/completions'),
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'model': 'gpt-4o-mini',
          'temperature': 0.6,
          'max_tokens': 120,
          'messages': [
            {'role': 'system', 'content': 'You are MindCore AI. Write a single warm, honest, human paragraph (max 80 words) reflecting the user\'s week back to them based on their mood data. Be specific to the numbers. Be like a trusted friend who has been watching them. Never be generic. Never use bullet points. Just one paragraph.'},
            {'role': 'user', 'content': prompt},
          ],
        }),
      ).timeout(const Duration(seconds: 15));

      if (res.statusCode != 200) return '';
      final body = jsonDecode(res.body);
      final text = (body['choices'] as List?)?.first?['message']?['content']?.toString().trim() ?? '';
      if (text.isEmpty) return '';

      await prefs.setString(_kInsightCache, text);
      await prefs.setInt(_kInsightCacheTs, DateTime.now().millisecondsSinceEpoch);
      return text;
    } catch (_) {
      return '';
    }
  }

  static String _buildInsightPrompt(WeeklyStats stats) {
    final parts = <String>[];
    if (stats.thisWeekAvg > 0) {
      parts.add('Mood average this week: ${(stats.thisWeekAvg * 2).toStringAsFixed(1)} out of 10');
    }
    if (stats.lastWeekAvg > 0) {
      parts.add('Mood average last week: ${(stats.lastWeekAvg * 2).toStringAsFixed(1)} out of 10');
    }
    parts.add('Check-ins this week: ${stats.checkInsThisWeek}');
    parts.add('Current streak: ${stats.streak} days');
    parts.add('Trend: ${stats.trendLabel}');
    return parts.join('. ');
  }

  // ── Short home card stat (one line) ────────────────────────────────────────────
  // Used by home screen insight card and Sunday notification.

  static Future<String> getHomeStatLine() async {
    final stats = await getWeeklyStats();
    if (stats.thisWeekAvg == 0) return '';
    final score = (stats.thisWeekAvg * 2).toStringAsFixed(1);
    return 'This week: mood ${stats.trendEmoji} $score — ${stats.checkInsThisWeek} check-in${stats.checkInsThisWeek == 1 ? '' : 's'}';
  }

  // ── Helpers ───────────────────────────────────────────────────────────────────

  static String _monthName(int m) {
    const names = ['','January','February','March','April','May','June',
        'July','August','September','October','November','December'];
    return names[m.clamp(1, 12)];
  }
}
