// lib/services/daily_plan_service.dart
import 'dart:convert';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

class PlanEntry {
  /// Date-only for grouping (00:00)
  final DateTime day;

  /// Exact timestamp when note was saved/updated
  final DateTime updatedAt;

  final String note;

  const PlanEntry({
    required this.day,
    required this.updatedAt,
    required this.note,
  });

  Map<String, dynamic> toJson() => {
    'day': DateFormat('yyyy-MM-dd').format(day),
    'ts': updatedAt.toIso8601String(),
    'note': note,
  };

  static PlanEntry fromJson(Map<String, dynamic> j) {
    final ts = DateTime.tryParse(j['ts'] as String? ?? '') ?? DateTime.now();
    final dayStr = j['day'] as String?;
    final dd = dayStr != null
        ? DateTime.tryParse(dayStr) ?? DateTime(ts.year, ts.month, ts.day)
        : DateTime(ts.year, ts.month, ts.day);
    final note = (j['note'] as String?)?.trim() ?? '';
    return PlanEntry(
      day: DateTime(dd.year, dd.month, dd.day),
      updatedAt: ts,
      note: note,
    );
  }
}

class DailyPlanService {
  // -----------------------------
  // Existing: daily plan note keys
  // -----------------------------
  static String _keyForDay(DateTime d) =>
      'daily_plan_${DateFormat('yyyy-MM-dd').format(DateTime(d.year, d.month, d.day))}';

  // ---------------------------------------
  // New: Daily goals counters (v1-friendly)
  // ---------------------------------------
  static const String _kGoalsRemaining = 'daily_goals_remaining';
  static const String _kGoalsTarget = 'daily_goals_target';
  static const String _kLastResetDayKey = 'daily_goals_last_reset_ymd';

  static const int _defaultTarget = 3;

  static String _ymd(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
          '${d.month.toString().padLeft(2, '0')}-'
          '${d.day.toString().padLeft(2, '0')}';

  /// Ensures the daily goals counters reset once per new local day.
  static Future<void> ensureDailyReset() async {
    final prefs = await SharedPreferences.getInstance();
    final today = _ymd(DateTime.now());
    final last = prefs.getString(_kLastResetDayKey);

    if (last == today) return;

    final target = prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
    await prefs.setInt(_kGoalsRemaining, target);
    await prefs.setString(_kLastResetDayKey, today);
  }

  /// Returns the configured daily target (default 3).
  static Future<int> getDailyTarget() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
  }

  /// Set daily target and align today's remaining to target (simple v1 behavior).
  static Future<void> setDailyTarget(int target) async {
    final prefs = await SharedPreferences.getInstance();
    final safe = target.clamp(1, 12);
    await prefs.setInt(_kGoalsTarget, safe);

    // make sure day is current, then align remaining to new target
    await ensureDailyReset();
    await prefs.setInt(_kGoalsRemaining, safe);
  }

  /// Get remaining goals for today (auto-resets if day changed).
  static Future<int> getRemaining() async {
    await ensureDailyReset();
    final prefs = await SharedPreferences.getInstance();
    final target = prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
    return prefs.getInt(_kGoalsRemaining) ?? target;
  }

  /// Decrement remaining by 1 (min 0). Returns new remaining.
  static Future<int> completeOneGoal() async {
    await ensureDailyReset();
    final prefs = await SharedPreferences.getInstance();
    final target = prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
    final current = prefs.getInt(_kGoalsRemaining) ?? target;
    final next = (current - 1).clamp(0, 999);
    await prefs.setInt(_kGoalsRemaining, next);
    return next;
  }

  /// Increment remaining by 1 (up to target). Returns new remaining.
  static Future<int> undoOneGoal() async {
    await ensureDailyReset();
    final prefs = await SharedPreferences.getInstance();
    final target = prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
    final current = prefs.getInt(_kGoalsRemaining) ?? target;
    final next = (current + 1).clamp(0, target);
    await prefs.setInt(_kGoalsRemaining, next);
    return next;
  }

  /// Force-reset today's remaining to the daily target (useful for testing/settings).
  static Future<int> resetTodayToTarget() async {
    final prefs = await SharedPreferences.getInstance();
    final target = prefs.getInt(_kGoalsTarget) ?? _defaultTarget;
    await prefs.setInt(_kGoalsRemaining, target);
    await prefs.setString(_kLastResetDayKey, _ymd(DateTime.now()));
    return target;
  }

  // -----------------------------------------
  // Existing functions: Plan note (unchanged)
  // -----------------------------------------

  /// Read today's note (empty if none). Backward compatible with legacy plain-string storage.
  static Future<String> getTodayNote() async {
    final prefs = await SharedPreferences.getInstance();
    final k = _keyForDay(DateTime.now());
    final raw = prefs.getString(k);
    if (raw == null || raw.isEmpty) return '';

    // Try JSON first
    try {
      final obj = jsonDecode(raw);
      if (obj is Map<String, dynamic>) {
        return (obj['note'] as String?)?.trim() ?? '';
      }
    } catch (_) {
      // fall through
    }

    // Legacy: stored as plain note string
    return raw.trim();
  }

  /// Save/overwrite today's note. Stores JSON with a 'ts' (updatedAt) field.
  static Future<void> saveTodayNote(String note) async {
    final prefs = await SharedPreferences.getInstance();
    final today = DateTime.now();
    final k = _keyForDay(today);
    final payload = jsonEncode({
      'day': DateFormat('yyyy-MM-dd').format(DateTime(today.year, today.month, today.day)),
      'ts': DateTime.now().toIso8601String(),
      'note': note.trim(),
    });
    await prefs.setString(k, payload);
  }

  /// Load plan entries between [from] and [to], inclusive, newest first.
  /// Backward compatible with legacy plain-string storage.
  static Future<List<PlanEntry>> getNotesInRange(DateTime from, DateTime to) async {
    final prefs = await SharedPreferences.getInstance();

    // normalize to date-only
    final start = DateTime(from.year, from.month, from.day);
    final end = DateTime(to.year, to.month, to.day);

    final out = <PlanEntry>[];
    for (DateTime d = end; !d.isBefore(start); d = d.subtract(const Duration(days: 1))) {
      final k = _keyForDay(d);
      final raw = prefs.getString(k);
      if (raw == null || raw.isEmpty) continue;

      // Try parse JSON
      try {
        final obj = jsonDecode(raw);
        if (obj is Map<String, dynamic>) {
          final entry = PlanEntry.fromJson(Map<String, dynamic>.from(obj));
          if (entry.note.isNotEmpty) out.add(entry);
          continue;
        }
      } catch (_) {}

      // Legacy: plain note string without timestamp → assume updatedAt at 09:00 that day
      final legacyNote = raw.trim();
      if (legacyNote.isNotEmpty) {
        out.add(
          PlanEntry(
            day: DateTime(d.year, d.month, d.day),
            updatedAt: DateTime(d.year, d.month, d.day, 9, 0),
            note: legacyNote,
          ),
        );
      }
    }
    return out;
  }
}
