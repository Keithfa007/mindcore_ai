import 'package:shared_preferences/shared_preferences.dart';

class TherapistModeConfig {
  final bool enabled;
  final String modeLabel;
  final bool reflectiveQuestions;
  final bool groundingBias;

  const TherapistModeConfig({
    required this.enabled,
    required this.modeLabel,
    required this.reflectiveQuestions,
    required this.groundingBias,
  });

  static const fallback = TherapistModeConfig(
    enabled: false,
    modeLabel: 'coach',
    reflectiveQuestions: true,
    groundingBias: true,
  );
}

class TherapistModeService {
  TherapistModeService._();

  static const String _kEnabled = 'therapist_mode_enabled_v1';
  static const String _kModeLabel = 'therapist_mode_label_v1';
  static const String _kReflectiveQuestions = 'therapist_mode_reflective_q_v1';
  static const String _kGroundingBias = 'therapist_mode_grounding_bias_v1';

  static Future<TherapistModeConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    return TherapistModeConfig(
      enabled: prefs.getBool(_kEnabled) ?? false,
      modeLabel: prefs.getString(_kModeLabel) ?? 'coach',
      reflectiveQuestions: prefs.getBool(_kReflectiveQuestions) ?? true,
      groundingBias: prefs.getBool(_kGroundingBias) ?? true,
    );
  }

  static Future<void> save(TherapistModeConfig config) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kEnabled, config.enabled);
    await prefs.setString(_kModeLabel, config.modeLabel);
    await prefs.setBool(_kReflectiveQuestions, config.reflectiveQuestions);
    await prefs.setBool(_kGroundingBias, config.groundingBias);
  }

  static Future<String> buildSystemOverlay() async {
    final config = await load();
    if (!config.enabled) return '';

    final parts = <String>[
      'Adopt a premium therapeutic coaching tone: calm, compassionate, non-judgmental, structured, and emotionally safe.',
      'Do not claim to diagnose, treat, or replace a licensed professional.',
      'Prefer emotional validation, gentle reflection, and one practical next step.',
    ];

    if (config.reflectiveQuestions) {
      parts.add('Use at most one reflective question when it helps deepen insight.');
    }

    if (config.groundingBias) {
      parts.add('When the user seems dysregulated, prioritize grounding before advice.');
    }

    switch (config.modeLabel.toLowerCase()) {
      case 'therapist':
        parts.add('Lean more reflective and emotionally attuned, while staying within supportive coaching boundaries.');
        break;
      case 'coach':
        parts.add('Lean practical, encouraging, and forward-moving.');
        break;
      case 'hybrid':
      default:
        parts.add('Blend therapist-style empathy with coach-style clarity and momentum.');
        break;
    }

    return parts.join(' ');
  }
}
