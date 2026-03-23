import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/data_privacy_service.dart';

/// Breathing presets used across the app (Settings + Breathe).
enum BreathePreset { box, equal, fourSevenEight, custom }

extension BreathePresetLabel on BreathePreset {
  String get label {
    switch (this) {
      case BreathePreset.box:
        return 'Box 4-4-4-4';
      case BreathePreset.equal:
        return 'Equal 5-5';
      case BreathePreset.fourSevenEight:
        return '4-7-8';
      case BreathePreset.custom:
        return 'Custom';
    }
  }
}

class SettingsService {
  SettingsService._();

  // ---------- Keys ----------
  static const _kThemeMode = 'theme_mode_v1'; // 0=system,1=light,2=dark

  static const _kBreathePreset   = 'breathe_preset_v1'; // 'box'|'equal'|'478'|'custom'
  static const _kBreatheDuration = 'breathe_duration_secs_v1'; // int seconds
  static const _kBreatheHaptics  = 'breathe_haptics_v1'; // bool

  static const _kDailyReminderEnabled = 'notif_daily_enabled_v1'; // bool
  static const _kDailyReminderHour    = 'notif_daily_hour_v1';    // int
  static const _kDailyReminderMinute  = 'notif_daily_min_v1';     // int

  // ---------- Backing store ----------
  static SharedPreferences? _prefs;
  static Future<SharedPreferences> get _p async =>
      _prefs ??= await SharedPreferences.getInstance();

  // ---------- Theme (ValueListenable used by main.dart) ----------
  static final ValueNotifier<ThemeMode> themeMode =
  ValueNotifier<ThemeMode>(ThemeMode.system);

  static Future<void> init() async {
    final p = await _p;
    final idx = p.getInt(_kThemeMode) ?? 0;
    themeMode.value = _decodeTheme(idx);
  }

  static Future<ThemeMode> getThemeMode() async {
    final p = await _p;
    final idx = p.getInt(_kThemeMode) ?? 0;
    return _decodeTheme(idx);
  }

  static Future<void> setThemeMode(ThemeMode mode) async {
    final p = await _p;
    themeMode.value = mode;
    await p.setInt(_kThemeMode, _encodeTheme(mode));
  }

  static int _encodeTheme(ThemeMode m) {
    switch (m) {
      case ThemeMode.light:
        return 1;
      case ThemeMode.dark:
        return 2;
      case ThemeMode.system:
      default:
        return 0;
    }
  }

  static ThemeMode _decodeTheme(int i) {
    switch (i) {
      case 1:
        return ThemeMode.light;
      case 2:
        return ThemeMode.dark;
      case 0:
      default:
        return ThemeMode.system;
    }
  }

  // ---------- Breathe settings ----------
  static Future<BreathePreset> getPreset() async {
    final p = await _p;
    final s = p.getString(_kBreathePreset) ?? 'box';
    switch (s) {
      case 'equal':
        return BreathePreset.equal;
      case '478':
        return BreathePreset.fourSevenEight;
      case 'custom':
        return BreathePreset.custom;
      case 'box':
      default:
        return BreathePreset.box;
    }
  }

  static Future<void> setPreset(BreathePreset preset) async {
    final p = await _p;
    final s = {
      BreathePreset.box: 'box',
      BreathePreset.equal: 'equal',
      BreathePreset.fourSevenEight: '478',
      BreathePreset.custom: 'custom',
    }[preset]!;
    await p.setString(_kBreathePreset, s);
  }

  static Future<int> getDurationSecs() async {
    final p = await _p;
    return p.getInt(_kBreatheDuration) ?? 60;
  }

  static Future<void> setDurationSecs(int seconds) async {
    final p = await _p;
    await p.setInt(_kBreatheDuration, seconds);
  }

  static Future<bool> getHaptics() async {
    final p = await _p;
    return p.getBool(_kBreatheHaptics) ?? true;
  }

  static Future<void> setHaptics(bool value) async {
    final p = await _p;
    await p.setBool(_kBreatheHaptics, value);
  }

  // ---------- Daily reminder (Notifications) ----------
  static Future<bool> getDailyReminderEnabled() async {
    final p = await _p;
    return p.getBool(_kDailyReminderEnabled) ?? false;
  }

  static Future<void> setDailyReminderEnabled(bool v) async {
    final p = await _p;
    await p.setBool(_kDailyReminderEnabled, v);
  }

  static Future<TimeOfDay> getDailyReminderTime() async {
    final p = await _p;
    final h = p.getInt(_kDailyReminderHour) ?? 8;
    final m = p.getInt(_kDailyReminderMinute) ?? 0;
    return TimeOfDay(hour: h, minute: m);
  }

  static Future<void> setDailyReminderTime(TimeOfDay t) async {
    final p = await _p;
    await p.setInt(_kDailyReminderHour, t.hour);
    await p.setInt(_kDailyReminderMinute, t.minute);
  }

  // ---------- Data clearing ----------
  static Future<void> clearLocalData() async {
    // Clear content/history first
    await DataPrivacyService.deleteAllLocalMindResetData();

    final p = await _p;

    // Remove known app keys. (Avoid full clear to keep user theme etc.)
    await p.remove(_kBreatheDuration);
    await p.remove(_kBreatheHaptics);
    await p.remove(_kBreathePreset);

    // Daily reminder prefs (optional to clear)
    await p.remove(_kDailyReminderEnabled);
    await p.remove(_kDailyReminderHour);
    await p.remove(_kDailyReminderMinute);

    // NOTE: If your tip/affirmation services store daily caches with
    // date-based keys, clear them inside those services to avoid nuking
    // unrelated preferences here.
  }
}
