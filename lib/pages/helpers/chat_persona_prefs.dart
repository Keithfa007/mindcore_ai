// lib/pages/helpers/chat_persona_prefs.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class PersonaProfile {
  final String presetName;
  final String profileText;

  const PersonaProfile({
    required this.presetName,
    required this.profileText,
  });

  Map<String, dynamic> toJson() => {
    'presetName': presetName,
    'profileText': profileText,
  };

  static PersonaProfile fromJson(Map<String, dynamic> j) {
    return PersonaProfile(
      presetName: (j['presetName'] ?? 'Coach+Therapist').toString(),
      profileText: (j['profileText'] ?? '').toString(),
    );
  }
}

class ChatPersonaPrefs {
  static const _kPersona = 'chat_persona_v1';

  /// Built-in presets (you can tweak the wording anytime).
  static const presets = <String, String>{
    'Coach+Therapist (Default)': '''
- Be warm, validating, and solution-focused.
- Keep it positive but realistic; avoid toxic positivity.
- Use reflective listening + gentle reframes.
- Give 1–2 micro-steps (2–10 minutes).
- End with one supportive question.
- Never shame; never catastrophize.
''',
    'Therapist (Gentle + Deep)': '''
- Lead with empathy and validation.
- Ask one thoughtful question per turn.
- Use gentle reframes and emotional naming.
- Encourage self-compassion and boundaries.
- Keep it calm, slow, and grounded.
''',
    'Coach (Action + Momentum)': '''
- Keep it upbeat and practical.
- Convert overwhelm into a short plan.
- Use simple bullet steps and “next best action”.
- Encourage accountability without guilt.
- End with: “What’s the smallest step you can do right now?”
''',
    'Motivator (Positive + Encouraging)': '''
- Keep the tone high and hopeful.
- Focus on strengths, wins, and possibilities.
- Use confident encouragement + quick steps.
- Avoid heavy language; keep it energizing.
''',
    'Minimalist (Short + Clear)': '''
- Extremely concise.
- 1 validation line + 1 reframe line.
- 1 micro-step + 1 question. No extra.
''',
  };

  static PersonaProfile defaultProfile() => PersonaProfile(
    presetName: 'Coach+Therapist (Default)',
    profileText: presets['Coach+Therapist (Default)']!,
  );

  static Future<PersonaProfile> loadPersona() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_kPersona);
    if (raw == null || raw.isEmpty) return defaultProfile();

    try {
      final j = jsonDecode(raw) as Map<String, dynamic>;
      final p = PersonaProfile.fromJson(j);

      // If stored preset name exists but text empty, restore from presets.
      if (p.profileText.trim().isEmpty && presets.containsKey(p.presetName)) {
        return PersonaProfile(presetName: p.presetName, profileText: presets[p.presetName]!.trim());
      }
      return p;
    } catch (_) {
      return defaultProfile();
    }
  }

  static Future<void> savePersona(PersonaProfile profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kPersona, jsonEncode(profile.toJson()));
  }

  static Future<void> setPreset(String presetName) async {
    final text = presets[presetName] ?? presets.values.first;
    await savePersona(PersonaProfile(presetName: presetName, profileText: text.trim()));
  }

  static Future<void> resetDefault() async {
    await savePersona(defaultProfile());
  }
}
