import 'package:mindcore_ai/services/unified_tts_service.dart';

class StreamingVoiceBridge {
  StreamingVoiceBridge._();

  static Future<void> begin({
    required String sessionId,
  }) {
    return UnifiedOpenAiTtsService.instance.beginChatStream(sessionId);
  }

  static void ingest({
    required String sessionId,
    required String fullText,
    required String moodLabel,
    required String messageId,
  }) {
    UnifiedOpenAiTtsService.instance.ingestChatStream(
      sessionId: sessionId,
      fullText: fullText,
      moodLabel: moodLabel,
      messageId: messageId,
    );
  }

  static Future<void> finish({
    required String sessionId,
    required String fullText,
    required String moodLabel,
    required String messageId,
  }) {
    return UnifiedOpenAiTtsService.instance.finishChatStream(
      sessionId: sessionId,
      fullText: fullText,
      moodLabel: moodLabel,
      messageId: messageId,
    );
  }

  static Future<void> stop() {
    return UnifiedOpenAiTtsService.instance.stopAll();
  }
}
