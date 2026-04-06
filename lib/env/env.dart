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

  // Fish Audio TTS
  static const fishAudioKey =
      String.fromEnvironment('FISH_AUDIO_API_KEY', defaultValue: '');

  // Default to the chosen voice — can be overridden via env
  static const fishAudioVoiceId =
      String.fromEnvironment('FISH_AUDIO_VOICE_ID',
          defaultValue: '0b74ead073f2474a904f69033535b98e');

  // Backend relay removed. These stay empty only for backward compatibility.
  static const voiceRelayBaseUrl = '';
  static const voiceRelayAuthToken = '';
}
