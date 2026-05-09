// lib/services/persona_service.dart
//
// Stores the user's persona preference (standard or feminine).
// Used by agent_prompts.dart to adjust AI tone and by
// live_voice_preferences.dart to select the active voice.

import 'package:shared_preferences/shared_preferences.dart';

enum PersonaStyle { standard, feminine }

class PersonaService {
  PersonaService._();

  static const _kPersonaStyle = 'persona_style_v1';

  static Future<PersonaStyle> getPersonaStyle() async {
    final prefs = await SharedPreferences.getInstance();
    final val   = prefs.getString(_kPersonaStyle) ?? 'standard';
    return val == 'feminine' ? PersonaStyle.feminine : PersonaStyle.standard;
  }

  static Future<void> setPersonaStyle(PersonaStyle style) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _kPersonaStyle,
      style == PersonaStyle.feminine ? 'feminine' : 'standard',
    );
  }
}
