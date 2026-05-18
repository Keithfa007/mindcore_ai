// lib/services/sleep_ritual_service.dart
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/services/notification_service.dart';

class SleepRitualService {
  SleepRitualService._();
  static final instance = SleepRitualService._();

  static const _prefix           = 'sleep_checkin_';
  static const _kEnabled         = 'sleep_ritual_enabled';
  static const _kEveningHour     = 'sleep_ritual_evening_hour';
  static const _kEveningMinute   = 'sleep_ritual_evening_minute';
  static const _kMorningHour     = 'sleep_ritual_morning_hour';
  static const _kMorningMinute   = 'sleep_ritual_morning_minute';

  String _dateKey(DateTime d) =>
      '$_prefix${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  String get _todayKey     => _dateKey(DateTime.now());
  String get _yesterdayKey => _dateKey(DateTime.now().subtract(const Duration(days: 1)));

  // ── Save ───────────────────────────────────────────────────────────────

  Future<void> saveEveningCheckIn({required int score, String? note}) async {
    final prefs    = await SharedPreferences.getInstance();
    final existing = await _load(_todayKey) ?? {};
    existing['eveningScore'] = score;
    if (note != null && note.trim().isNotEmpty) existing['eveningNote'] = note.trim();
    existing['eveningTime'] = DateTime.now().toIso8601String();
    await prefs.setString(_todayKey, jsonEncode(existing));
    if (kDebugMode) print('SleepRitual: evening=$score saved');
  }

  Future<void> saveMorningCheckIn({required int score, String? note}) async {
    final prefs    = await SharedPreferences.getInstance();
    final existing = await _load(_todayKey) ?? {};
    existing['morningScore'] = score;
    if (note != null && note.trim().isNotEmpty) existing['morningNote'] = note.trim();
    existing['morningTime'] = DateTime.now().toIso8601String();
    await prefs.setString(_todayKey, jsonEncode(existing));
    if (kDebugMode) print('SleepRitual: morning=$score saved');
  }

  // ── Load ───────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> getTodayCheckIn()      => _load(_todayKey);
  Future<Map<String, dynamic>?> getLastNightCheckIn()  => _load(_yesterdayKey);

  Future<bool> hasEveningCheckInToday() async {
    final d = await getTodayCheckIn();
    return d?['eveningScore'] != null;
  }

  Future<bool> hasMorningCheckInToday() async {
    final d = await getTodayCheckIn();
    return d?['morningScore'] != null;
  }

  /// Returns up to [days] days of check-ins, newest first.
  Future<List<Map<String, dynamic>>> getRecentCheckIns({int days = 14}) async {
    final prefs   = await SharedPreferences.getInstance();
    final results = <Map<String, dynamic>>[];
    for (var i = 0; i < days; i++) {
      final d   = DateTime.now().subtract(Duration(days: i));
      final key = _dateKey(d);
      final raw = prefs.getString(key);
      if (raw == null) continue;
      try {
        final data = jsonDecode(raw) as Map<String, dynamic>;
        data['date'] = key.replaceFirst(_prefix, '');
        results.add(data);
      } catch (_) {}
    }
    return results;
  }

  // ── Settings ────────────────────────────────────────────────────────────

  Future<bool>      getEnabled()     async {
    final p = await SharedPreferences.getInstance();
    return p.getBool(_kEnabled) ?? false;
  }

  Future<TimeOfDay> getEveningTime() async {
    final p = await SharedPreferences.getInstance();
    return TimeOfDay(hour: p.getInt(_kEveningHour) ?? 22, minute: p.getInt(_kEveningMinute) ?? 0);
  }

  Future<TimeOfDay> getMorningTime() async {
    final p = await SharedPreferences.getInstance();
    return TimeOfDay(hour: p.getInt(_kMorningHour) ?? 7, minute: p.getInt(_kMorningMinute) ?? 0);
  }

  Future<void> setEnabled(bool v)          async => (await SharedPreferences.getInstance()).setBool(_kEnabled, v);
  Future<void> setEveningTime(TimeOfDay t) async {
    final p = await SharedPreferences.getInstance();
    await p.setInt(_kEveningHour,   t.hour);
    await p.setInt(_kEveningMinute, t.minute);
  }
  Future<void> setMorningTime(TimeOfDay t) async {
    final p = await SharedPreferences.getInstance();
    await p.setInt(_kMorningHour,   t.hour);
    await p.setInt(_kMorningMinute, t.minute);
  }

  // ── Notifications ──────────────────────────────────────────────────────────

  Future<void> scheduleNotifications() async {
    await NotificationService.instance.scheduleSleepRitualNotifications(
      eveningTime: await getEveningTime(),
      morningTime: await getMorningTime(),
    );
  }

  Future<void> cancelNotifications() =>
      NotificationService.instance.cancelSleepRitualNotifications();

  // ── Internal ─────────────────────────────────────────────────────────────

  Future<Map<String, dynamic>?> _load(String key) async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(key);
    if (raw == null) return null;
    try { return jsonDecode(raw) as Map<String, dynamic>; } catch (_) { return null; }
  }
}
