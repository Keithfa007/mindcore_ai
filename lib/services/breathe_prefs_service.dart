import 'package:shared_preferences/shared_preferences.dart';

/// Public helper to control BreatheScreen defaults.
///
/// NOTE: These keys must match the keys used in `lib/pages/breathe_screen.dart`.
class BreathePrefsService {
  static const String _kPreset = 'breathe_preset_v1';
  static const String _kTargetCycles = 'breathe_target_cycles_v1';
  static const String _kTtsCues = 'breathe_tts_v1';

  /// Presets used by BreatheScreen:
  ///  - 'box'
  ///  - 'equal'
  ///  - '478'
  ///  - 'custom'
  static Future<void> setPreset(String preset) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kPreset, preset);
  }

  /// Set how many cycles the user should do. 0 = infinite.
  static Future<void> setTargetCycles(int cycles) async {
    final p = await SharedPreferences.getInstance();
    await p.setInt(_kTargetCycles, cycles);
  }

  /// Enable/disable spoken cues inside the breathing session (separate from app TTS).
  static Future<void> setBreathingTtsCues(bool enabled) async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_kTtsCues, enabled);
  }

  /// Convenience for the v1 Quick Reset flow.
  static Future<void> configureForMood(String moodLabel) async {
    final m = moodLabel.toLowerCase();
    final anxious = m.contains('anx') ||
        m.contains('panic') ||
        m.contains('stress') ||
        m.contains('overwhelm');

    if (anxious) {
      await setPreset('478');
      await setTargetCycles(3);
    } else {
      await setPreset('box');
      await setTargetCycles(4);
    }

    // Keep breathing cues off by default (gentler) unless you want them later.
    await setBreathingTtsCues(false);
  }
}
