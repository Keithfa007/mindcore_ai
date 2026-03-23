import 'dart:convert';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DailyGoals {
  final bool breatheDone;
  final bool reflectionDone;

  const DailyGoals({required this.breatheDone, required this.reflectionDone});

  int get total => 2;
  int get completed => (breatheDone ? 1 : 0) + (reflectionDone ? 1 : 0);
  int get remaining => total - completed;
}

class DailyGoalsService {
  static String _todayKey(String base) =>
      '${base}_${DateFormat('yyyy-MM-dd').format(DateTime.now())}';

  /// Mark “completed one breathing session today”.
  static Future<void> markBreatheDoneToday() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_todayKey('goal_breathe'), true);
  }

  /// Check if a breathing session was done today.
  static Future<bool> _getBreatheDoneToday() async {
    final p = await SharedPreferences.getInstance();
    return p.getBool(_todayKey('goal_breathe')) ?? false;
  }

  /// Reflection is considered “done” if journal has an entry for today.
  static Future<bool> _hasReflectionToday() async {
    final p = await SharedPreferences.getInstance();
    final raw = p.getString('journal_entries');
    if (raw == null || raw.isEmpty) return false;
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    try {
      final list = (jsonDecode(raw) as List).cast<Map>();
      for (final e in list) {
        final tsStr = e['ts'] as String?;
        if (tsStr == null) continue;
        final d = DateTime.tryParse(tsStr);
        if (d == null) continue;
        if (DateFormat('yyyy-MM-dd').format(d) == today) return true;
      }
    } catch (_) {}
    return false;
  }

  /// Returns today’s goals status.
  static Future<DailyGoals> getToday() async {
    final breathe = await _getBreatheDoneToday();
    final reflect = await _hasReflectionToday();
    return DailyGoals(breatheDone: breathe, reflectionDone: reflect);
  }
}
