import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:mindcore_ai/config/app_config.dart';
import 'package:mindcore_ai/env/env.dart';

class RealtimeVoiceRelay {
  RealtimeVoiceRelay._();

  static String get _base {
    final fromDotEnv = (dotenv.env['VOICE_RELAY_BASE_URL'] ?? '').trim();
    final fromDefine = Env.voiceRelayBaseUrl.trim();
    final fromConfig = AppConfig.voiceRelayBaseUrl.trim();
    final resolved = fromDotEnv.isNotEmpty
        ? fromDotEnv
        : (fromDefine.isNotEmpty ? fromDefine : fromConfig);
    return resolved.replaceAll(RegExp(r'/+$'), '');
  }

  static String get _relayToken {
    final fromDotEnv = (dotenv.env['VOICE_RELAY_AUTH_TOKEN'] ?? '').trim();
    final fromDefine = Env.voiceRelayAuthToken.trim();
    final fromConfig = AppConfig.voiceRelayAuthToken.trim();
    return fromDotEnv.isNotEmpty
        ? fromDotEnv
        : (fromDefine.isNotEmpty ? fromDefine : fromConfig);
  }

  static bool get isConfigured => _base.isNotEmpty;

  static Map<String, String> get _headers {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (_relayToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_relayToken';
    }
    return headers;
  }

  static Future<Uint8List?> synthesize({
    required String text,
    required String voice,
    required double speed,
    String format = 'wav',
    String model = 'gpt-4o-mini-tts',
    String surface = 'chat',
    String moodLabel = 'neutral',
  }) async {
    if (!isConfigured) return null;

    try {
      final res = await http.post(
        Uri.parse('$_base/v1/voice/tts'),
        headers: _headers,
        body: jsonEncode({
          'text': text,
          'voice': voice,
          'speed': speed,
          'format': format,
          'model': model,
          'surface': surface,
          'moodLabel': moodLabel,
        }),
      );

      if (res.statusCode != 200) return null;
      return Uint8List.fromList(res.bodyBytes);
    } catch (_) {
      return null;
    }
  }

  static Future<Map<String, dynamic>?> createRealtimeSession({
    String voice = 'nova',
    String model = 'gpt-4o-realtime-preview',
    String? instructions,
  }) async {
    if (!isConfigured) return null;
    try {
      final res = await http.post(
        Uri.parse('$_base/v1/voice/realtime/session'),
        headers: _headers,
        body: jsonEncode({
          'voice': voice,
          'model': model,
          if (instructions != null && instructions.trim().isNotEmpty)
            'instructions': instructions.trim(),
        }),
      );
      if (res.statusCode != 200) return null;
      final data = jsonDecode(res.body);
      if (data is Map<String, dynamic>) return data;
      return null;
    } catch (_) {
      return null;
    }
  }
}
