import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/tts_chunk_coordinator.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

class UnifiedOpenAiTtsService {
  UnifiedOpenAiTtsService._();
  static final UnifiedOpenAiTtsService instance = UnifiedOpenAiTtsService._();

  final TtsChunkCoordinator _chatCoordinator = TtsChunkCoordinator();

  Future<void> init() async {
    await OpenAiTtsService.instance.init();
    await LiveVoicePreferences.instance.load();
  }

  Future<void> stopAll() async {
    _chatCoordinator.cancel();
    await OpenAiTtsService.instance.stop();
  }

  Future<void> beginChatStream(String sessionId) async {
    await LiveVoicePreferences.instance.load();
    _chatCoordinator.startSession(sessionId);
  }

  void ingestChatStream({
    required String sessionId,
    required String fullText,
    required String moodLabel,
    required String messageId,
  }) {
    if (!LiveVoicePreferences.instance.autoSpeakChatReplies) return;
    if (!LiveVoicePreferences.instance.streamChatReplies) return;
    if (!OpenAiTtsService.instance.enabled) return;
    if (!OpenAiTtsService.instance.isSurfaceEnabled(TtsSurface.chat)) return;

    _chatCoordinator.ingest(
      sessionId: sessionId,
      fullText: fullText,
      player: (chunk, index, _) async {
        await OpenAiTtsService.instance.speak(
          chunk,
          moodLabel: moodLabel,
          messageId: '${messageId}_chunk_$index',
          surface: TtsSurface.chat,
        );
      },
    );
  }

  Future<void> finishChatStream({
    required String sessionId,
    required String fullText,
    required String moodLabel,
    required String messageId,
  }) async {
    if (!LiveVoicePreferences.instance.autoSpeakChatReplies) return;
    if (!OpenAiTtsService.instance.enabled) return;
    if (!OpenAiTtsService.instance.isSurfaceEnabled(TtsSurface.chat)) return;

    await _chatCoordinator.finish(
      sessionId: sessionId,
      fullText: fullText,
      player: (chunk, index, _) async {
        await OpenAiTtsService.instance.speak(
          chunk,
          moodLabel: moodLabel,
          messageId: '${messageId}_chunk_$index',
          surface: TtsSurface.chat,
        );
      },
    );
  }

  Future<void> previewCalmVoice() async {
    await OpenAiTtsService.instance.speak(
      'Hi Keith. I am here with you. Slow your breath, soften your shoulders, and let this moment feel a little lighter.',
      moodLabel: 'calm',
      messageId: 'voice_preview_calm',
      surface: TtsSurface.dailyMotivation,
      force: true,
    );
  }

  Future<void> previewProfile(String profile) async {
    await LiveVoicePreferences.instance.setChatVoiceProfile(profile);
    String line = 'You are safe. Let us take one clear, steady breath and move forward gently.';
    if (profile == 'grounding_therapist') {
      line = 'I am here with you. Notice your feet, relax your jaw, and take this one step slowly.';
    } else if (profile == 'motivational_push') {
      line = 'You have got this. One calm breath, one focused action, and we move forward together.';
    }
    await OpenAiTtsService.instance.speak(
      line,
      moodLabel: 'calm',
      messageId: 'voice_preview_' + profile,
      surface: TtsSurface.chat,
      force: true,
    );
  }
}
