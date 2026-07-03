class Env {
  static const openaiKey =
      String.fromEnvironment('OPENAI_API_KEY', defaultValue: '');

  static const stripeSecret =
      String.fromEnvironment('STRIPE_SECRET_KEY', defaultValue: '');

  static const stripePublishable =
      String.fromEnvironment('STRIPE_PUBLISHABLE_KEY', defaultValue: '');

  static const googleClientId =
      String.fromEnvironment('GOOGLE_CLIENT_ID', defaultValue: '');

  static const ytKey =
      String.fromEnvironment('YOUTUBE_API_KEY', defaultValue: '');

  // ElevenLabs TTS (replaced Fish Audio July 2026)
  static const elevenLabsKey =
      String.fromEnvironment('ELEVENLABS_API_KEY', defaultValue: '');

  // Legacy Fish Audio keys — kept for backward compatibility only
  static const fishAudioKey =
      String.fromEnvironment('FISH_AUDIO_API_KEY', defaultValue: '');
  static const fishAudioVoiceId =
      String.fromEnvironment('FISH_AUDIO_VOICE_ID',
          defaultValue: '0b74ead073f2474a904f69033535b98e');

  // Backend relay removed. These stay empty only for backward compatibility.
  static const voiceRelayBaseUrl = '';
  static const voiceRelayAuthToken = '';
}
