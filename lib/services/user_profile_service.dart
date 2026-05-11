// lib/services/user_profile_service.dart
//
// Stores onboarding answers and builds a user profile block
// that is injected into every AI system prompt.
// This means the AI knows who the user is from their very first message.

import 'package:shared_preferences/shared_preferences.dart';

class UserProfileService {
  UserProfileService._();

  // ── Preference keys ──────────────────────────────────────────────────────
  static const _kName          = 'user_display_name';
  static const _kFeeling       = 'onboarding_feeling';
  static const _kReasons       = 'onboarding_reasons';       // comma-separated
  static const _kSupportStyle  = 'onboarding_support_style';
  static const _kOpenness      = 'onboarding_openness';
  static const _kInitialNote   = 'onboarding_initial_note';

  // ── Save ────────────────────────────────────────────────────────────────────

  static Future<void> saveProfile({
    String? name,
    String? feeling,
    List<String>? reasons,
    String? supportStyle,
    String? openness,
    String? initialNote,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (name        != null && name.isNotEmpty)        await prefs.setString(_kName,         name);
    if (feeling     != null && feeling.isNotEmpty)     await prefs.setString(_kFeeling,      feeling);
    if (reasons     != null && reasons.isNotEmpty)     await prefs.setString(_kReasons,      reasons.join(','));
    if (supportStyle != null && supportStyle.isNotEmpty) await prefs.setString(_kSupportStyle, supportStyle);
    if (openness    != null && openness.isNotEmpty)    await prefs.setString(_kOpenness,     openness);
    if (initialNote != null && initialNote.isNotEmpty) await prefs.setString(_kInitialNote,  initialNote);
  }

  // ── Load ────────────────────────────────────────────────────────────────────

  static Future<String> getName() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kName) ?? '';
  }

  static Future<String> getInitialNote() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kInitialNote) ?? '';
  }

  // ── Build profile block for AI system prompt ─────────────────────────────────
  // Returns empty string if no profile exists yet.

  static Future<String> buildProfileBlock() async {
    try {
      final prefs       = await SharedPreferences.getInstance();
      final name        = prefs.getString(_kName)         ?? '';
      final feeling     = prefs.getString(_kFeeling)      ?? '';
      final reasons     = prefs.getString(_kReasons)      ?? '';
      final support     = prefs.getString(_kSupportStyle) ?? '';
      final openness    = prefs.getString(_kOpenness)     ?? '';
      final note        = prefs.getString(_kInitialNote)  ?? '';

      // Only inject if at least one field is set
      if (name.isEmpty && feeling.isEmpty && reasons.isEmpty &&
          support.isEmpty && openness.isEmpty && note.isEmpty) {
        return '';
      }

      final buf = StringBuffer();
      buf.writeln('── USER PROFILE (from onboarding) ───────────────────────────────────────────');
      if (name.isNotEmpty)
        buf.writeln('Name: $name');
      if (feeling.isNotEmpty)
        buf.writeln('How they were feeling when they joined: $feeling');
      if (reasons.isNotEmpty)
        buf.writeln('What brings them here: ${reasons.replaceAll(',', ', ')}');
      if (support.isNotEmpty)
        buf.writeln('Support preference: $support');
      if (openness.isNotEmpty)
        buf.writeln('Openness level: $openness');
      if (note.isNotEmpty)
        buf.writeln('What they shared before their first session: $note');
      buf.writeln('Honour these preferences every time. If openness is private or moderate, never push harder than they offer. Use their name naturally if they provided one.');
      buf.writeln();
      return buf.toString();
    } catch (_) {
      return '';
    }
  }
}
