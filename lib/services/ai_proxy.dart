import 'package:firebase_auth/firebase_auth.dart';

/// Central config + auth for the MindCore key-holding proxy (Cloudflare Worker).
///
/// The app never holds the OpenAI or ElevenLabs keys. Instead it calls this
/// proxy with the signed-in user's Firebase ID token, and the proxy attaches
/// the real key server-side. See `cloudflare-proxy/` in the repo.
class AiProxy {
  /// Public base URL of the proxy. This is NOT a secret — the security is the
  /// Firebase token check inside the Worker, not the URL.
  static const String base = 'https://mindcore-proxy.mindcoreai.workers.dev';

  /// OpenAI chat/completions endpoint (proxied).
  static Uri chat() => Uri.parse('$base/chat');

  /// ElevenLabs text-to-speech endpoint (proxied). [path] is everything that
  /// followed `/v1/text-to-speech/` before, e.g. `<voiceId>` or
  /// `<voiceId>/stream?output_format=...`.
  static Uri tts(String path) => Uri.parse('$base/tts/$path');

  /// The current user's Firebase ID token, or null if nobody is signed in.
  /// Used as the Bearer token when calling the proxy.
  static Future<String?> idToken() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return null;
    return user.getIdToken();
  }
}
