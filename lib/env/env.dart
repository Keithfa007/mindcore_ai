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

  // Backend relay removed. These stay empty only for backward compatibility.
  static const voiceRelayBaseUrl = '';
  static const voiceRelayAuthToken = '';
}
