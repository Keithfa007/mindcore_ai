// lib/services/wins_service.dart
//
// Stores daily "wins" — two quick answers that capture what went right.
// Data lives in SharedPreferences, keyed by date.
// Feeds into the weekly report and eventually the 90-day Mirror.

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class DailyWin {
  final String date;    // YYYY-MM-DD
  final String win1;   // "One thing that went okay today"
  final String win2;   // "One thing you did for yourself"
  final DateTime savedAt;

  const DailyWin({
    required this.date,
    required this.win1,
    required this.win2,
    required this.savedAt,
  });

  Map<String, dynamic> toJson() => {
    'win1': win1,
    'win2': win2,
    'savedAt': savedAt.toIso8601String(),
  };

  factory DailyWin.fromJson(String date, Map<String, dynamic> j) => DailyWin(
    date:    date,
    win1:    j['win1']?.toString()   ?? '',
    win2:    j['win2']?.toString()   ?? '',
    savedAt: DateTime.tryParse(j['savedAt']?.toString() ?? '') ?? DateTime.now(),
  );
}

class WinsService {
  WinsService._();
  static final instance = WinsService._();

  static const _prefix = 'daily_win_';

  String _key(DateTime d) =>
      '$_prefix${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  String _dateStr(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  // ── Save ────────────────────────────────────────────────────────────

  Future<void> saveToday({required String win1, required String win2}) async {
    final prefs = await SharedPreferences.getInstance();
    final now   = DateTime.now();
    final win   = DailyWin(date: _dateStr(now), win1: win1.trim(), win2: win2.trim(), savedAt: now);
    await prefs.setString(_key(now), jsonEncode(win.toJson()));
    if (kDebugMode) print('WinsService: saved win for ${win.date}');
  }

  // ── Load ────────────────────────────────────────────────────────────

  Future<bool> hasWinToday() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.containsKey(_key(DateTime.now()));
  }

  Future<DailyWin?> getToday() => _load(DateTime.now());

  Future<DailyWin?> _load(DateTime d) async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(_key(d));
    if (raw == null) return null;
    try {
      return DailyWin.fromJson(_dateStr(d), jsonDecode(raw) as Map<String, dynamic>);
    } catch (_) { return null; }
  }

  /// Returns up to [days] recent wins, newest first.
  Future<List<DailyWin>> getRecent({int days = 30}) async {
    final prefs   = await SharedPreferences.getInstance();
    final results = <DailyWin>[];
    for (var i = 0; i < days; i++) {
      final d   = DateTime.now().subtract(Duration(days: i));
      final raw = prefs.getString(_key(d));
      if (raw == null) continue;
      try {
        results.add(DailyWin.fromJson(_dateStr(d), jsonDecode(raw) as Map<String, dynamic>));
      } catch (_) {}
    }
    return results;
  }

  /// Delete a specific day's win.
  Future<void> delete(DateTime d) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key(d));
  }
}
