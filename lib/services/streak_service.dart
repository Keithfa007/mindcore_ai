// lib/services/streak_service.dart
//
// Calculates the user's current logging streak (consecutive days with
// at least one mood entry). Pure Dart, no AI calls.

import 'package:mindcore_ai/services/mood_log_service.dart';

class StreakService {
  /// Returns the current streak in days.
  /// Today counts if there is already an entry today.
  static Future<int> currentStreak() async {
    final all = await MoodRepo.instance.fetchAll();
    if (all.isEmpty) return 0;

    // Build a set of day keys that have at least one entry
    final loggedDays = <String>{};
    for (final e in all) {
      loggedDays.add(_dayKey(e.timestamp));
    }

    final today = DateTime.now();
    int streak = 0;

    // Walk backwards from today until we find a day with no entry
    for (int i = 0; i <= 365; i++) {
      final day = today.subtract(Duration(days: i));
      final key = _dayKey(day);
      if (loggedDays.contains(key)) {
        streak++;
      } else {
        // Allow a one-day gap only for today (user hasn't logged yet today)
        if (i == 0) continue;
        break;
      }
    }

    return streak;
  }

  static String _dayKey(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
