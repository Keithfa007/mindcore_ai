import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

class TtsReplayService {
  static String _textKey(TtsSurface surface) => 'tts_last_text_${surface.name}';
  static String _moodKey(TtsSurface surface) => 'tts_last_mood_${surface.name}';
  static String _messageKey(TtsSurface surface) => 'tts_last_message_${surface.name}';

  static Future<void> remember(
    TtsSurface surface,
    String text, {
    String moodLabel = 'calm',
    String? messageId,
  }) async {
    final cleaned = text.trim();
    if (cleaned.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_textKey(surface), cleaned);
    await prefs.setString(_moodKey(surface), moodLabel);
    await prefs.setString(
      _messageKey(surface),
      messageId ?? 'replay_${surface.name}_${cleaned.hashCode}',
    );
  }

  static Future<String?> getLastText(TtsSurface surface) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_textKey(surface));
  }

  static Future<bool> hasReplay(TtsSurface surface) async {
    final text = await getLastText(surface);
    return text != null && text.trim().isNotEmpty;
  }

  static Future<bool> replayLast(
    TtsSurface surface, {
    bool force = true,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final text = prefs.getString(_textKey(surface))?.trim() ?? '';
    if (text.isEmpty) return false;
    final mood = prefs.getString(_moodKey(surface)) ?? 'calm';
    final messageId = prefs.getString(_messageKey(surface)) ??
        'replay_${surface.name}_${text.hashCode}';
    return OpenAiTtsService.instance.speak(
      text,
      moodLabel: mood,
      surface: surface,
      messageId: messageId,
      force: force,
    );
  }
}
