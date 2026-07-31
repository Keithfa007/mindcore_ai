// lib/services/onboarding_taste_service.dart
//
// Generates the single warm, personalised "taste" reply shown during the new
// onboarding, streaming tokens as they arrive. It reuses the secure Cloudflare
// proxy (no API keys in the app) via the signed-in user's Firebase ID token —
// this includes anonymous users, so the taste works before a real account is
// created. It never throws: on any error or missing token it falls back to a
// warm pre-written reply so onboarding always flows.
import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:mindcore_ai/services/ai_proxy.dart';

class OnboardingTasteService {
  static const _model = 'gpt-4o-mini';

  /// Streams one warm reply personalised to [feeling] + [timing].
  /// Emits partial text through [onDelta]; returns the full text.
  static Future<String> streamTaste({
    required String feeling,
    required String timing,
    required Future<void> Function(String delta) onDelta,
  }) async {
    final fallback = _fallback(feeling, timing);

    // Crisis safety: if the picked feeling is a heavy one, we still reply warmly,
    // but the real chat has full crisis detection. This taste is intentionally
    // gentle and never gives medical or crisis instructions.
    final idToken = await AiProxy.idToken();
    if (idToken == null) {
      await onDelta(fallback);
      return fallback;
    }

    final system =
        'You are MindCore, a warm, human companion for someone who often feels alone. '
        'This is the very first thing a brand-new user hears from you, during onboarding. '
        'They just told you what weighs on them most and when it hits hardest. '
        'Reply in 3 to 4 short sentences: gently name their specific feeling and timing, '
        'validate it without cliches, remind them they are not alone and that reaching out '
        'already took strength, then end with one soft question inviting them to keep talking. '
        'Warm, plain language. No lists, no emojis, no markdown, no dashes. '
        'Never mention being an AI, a model, or a program.';
    final userMsg = 'What weighs on me most: $feeling. When it hits hardest: $timing.';

    final client = http.Client();
    final buffer = StringBuffer();
    try {
      final request = http.Request('POST', AiProxy.chat());
      request.headers.addAll({
        'Authorization': 'Bearer $idToken',
        'Content-Type': 'application/json',
      });
      request.body = jsonEncode({
        'model': _model,
        'messages': [
          {'role': 'system', 'content': system},
          {'role': 'user', 'content': userMsg},
        ],
        'temperature': 0.6,
        'max_tokens': 220,
        'stream': true,
      });

      final response =
          await client.send(request).timeout(const Duration(seconds: 25));

      if (response.statusCode != 200) {
        await onDelta(fallback);
        return fallback;
      }

      final lines = response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final raw in lines) {
        final line = raw.trim();
        if (!line.startsWith('data:')) continue;
        final data = line.substring(5).trim();
        if (data == '[DONE]') break;
        try {
          final json = jsonDecode(data) as Map<String, dynamic>;
          final choices = json['choices'] as List?;
          if (choices == null || choices.isEmpty) continue;
          final first = choices.first;
          if (first is! Map<String, dynamic>) continue;
          final deltaMap = first['delta'];
          if (deltaMap is! Map<String, dynamic>) continue;
          final delta = deltaMap['content']?.toString() ?? '';
          if (delta.isNotEmpty) {
            buffer.write(delta);
            await onDelta(delta);
          }
        } catch (_) {}
      }

      final text = buffer.toString().trim();
      if (text.isEmpty) {
        await onDelta(fallback);
        return fallback;
      }
      return text;
    } on TimeoutException {
      if (buffer.toString().trim().isEmpty) {
        await onDelta(fallback);
        return fallback;
      }
      return buffer.toString().trim();
    } catch (_) {
      if (buffer.toString().trim().isEmpty) {
        await onDelta(fallback);
        return fallback;
      }
      return buffer.toString().trim();
    } finally {
      client.close();
    }
  }

  static String _fallback(String feeling, String timing) =>
      "I hear you, and I'm really glad you told me. Feeling $feeling $timing is one of "
      "the heaviest times, because the world goes quiet and the thoughts get loud. "
      "Reaching out already took something real, and you're not alone in this. "
      "Do you want to tell me a little more about what it's been like?";
}
