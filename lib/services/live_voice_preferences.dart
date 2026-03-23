import 'package:shared_preferences/shared_preferences.dart';

class LiveVoicePreferences {
  LiveVoicePreferences._();
  static final LiveVoicePreferences instance = LiveVoicePreferences._();

  static const _kAutoSpeakChatReplies = 'voice_auto_speak_chat_replies_v1';
  static const _kStreamChatReplies = 'voice_stream_chat_replies_v1';
  static const _kInterruptOnNewMessage = 'voice_interrupt_on_new_message_v1';
  static const _kReplayAllowed = 'voice_replay_allowed_v1';
  static const _kChatStreamingVoice = 'live_voice_chat_streaming_v1';
  static const _kAiBreathingCoach = 'ai_breathing_coach_enabled_v1';
  static const _kChatVoiceProfile = 'live_voice_chat_profile_v1';
  static const _kAmbientBlendPreset = 'live_voice_ambient_blend_v1';
  static const _kAmbientBlendLevel = 'live_voice_ambient_level_v1';

  bool _autoSpeakChatReplies = true;
  bool _streamChatReplies = true;
  bool _interruptOnNewMessage = true;
  bool _replayAllowed = true;
  String _chatVoiceProfile = 'auto';
  String _ambientBlendPreset = 'off';
  double _ambientBlendLevel = 0.18;

  bool get autoSpeakChatReplies => _autoSpeakChatReplies;
  bool get streamChatReplies => _streamChatReplies;
  bool get interruptOnNewMessage => _interruptOnNewMessage;
  bool get replayAllowed => _replayAllowed;
  String get chatVoiceProfile => _chatVoiceProfile;
  String get ambientBlendPreset => _ambientBlendPreset;
  double get ambientBlendLevel => _ambientBlendLevel;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _autoSpeakChatReplies = prefs.getBool(_kAutoSpeakChatReplies) ?? true;
    _streamChatReplies = prefs.getBool(_kStreamChatReplies) ?? true;
    _interruptOnNewMessage = prefs.getBool(_kInterruptOnNewMessage) ?? true;
    _replayAllowed = prefs.getBool(_kReplayAllowed) ?? true;
    _chatVoiceProfile = prefs.getString(_kChatVoiceProfile) ?? 'auto';
    _ambientBlendPreset = prefs.getString(_kAmbientBlendPreset) ?? 'off';
    _ambientBlendLevel = prefs.getDouble(_kAmbientBlendLevel) ?? 0.18;
  }

  Future<void> setAutoSpeakChatReplies(bool value) async {
    _autoSpeakChatReplies = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kAutoSpeakChatReplies, value);
  }

  Future<void> setStreamChatReplies(bool value) async {
    _streamChatReplies = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kStreamChatReplies, value);
  }

  Future<void> setInterruptOnNewMessage(bool value) async {
    _interruptOnNewMessage = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kInterruptOnNewMessage, value);
  }

  Future<void> setReplayAllowed(bool value) async {
    _replayAllowed = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kReplayAllowed, value);
  }

  Future<void> setChatVoiceProfile(String value) async {
    final v = value.trim().toLowerCase();
    String normalized = 'auto';
    if (v == 'calm_coach' || v == 'calm coach') {
      normalized = 'calm_coach';
    } else if (v == 'grounding_therapist' || v == 'grounding therapist') {
      normalized = 'grounding_therapist';
    } else if (v == 'motivational_push' || v == 'motivational push') {
      normalized = 'motivational_push';
    }
    _chatVoiceProfile = normalized;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kChatVoiceProfile, normalized);
  }

  Future<void> setAmbientBlendPreset(String value) async {
    final v = value.trim();
    String normalized = 'off';
    if (v == '174' || v == '285' || v == '396' || v == '417' || v == '432' || v == '528') {
      normalized = v;
    }
    _ambientBlendPreset = normalized;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kAmbientBlendPreset, normalized);
  }

  Future<void> setAmbientBlendLevel(double value) async {
    _ambientBlendLevel = value.clamp(0.0, 0.6);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_kAmbientBlendLevel, _ambientBlendLevel);
  }



  // Compatibility aliases for older call sites.
  Future<void> setVoiceProfile(String value) async => setChatVoiceProfile(value);
  Future<void> setAmbientPreset(String value) async => setAmbientBlendPreset(value);
  Future<void> setAmbientLevel(double value) async => setAmbientBlendLevel(value);

  static Future<bool> getChatStreamingVoiceEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kChatStreamingVoice) ?? true;
  }

  static Future<void> setChatStreamingVoiceEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kChatStreamingVoice, value);
  }

  static Future<bool> getAiBreathingCoachEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kAiBreathingCoach) ?? true;
  }

  static Future<void> setAiBreathingCoachEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kAiBreathingCoach, value);
  }
}
