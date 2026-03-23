import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class AiBreathingCoach {
  final String inhale;
  final String exhale;
  final String hold;

  const AiBreathingCoach({
    required this.inhale,
    required this.exhale,
    required this.hold,
  });

  factory AiBreathingCoach.fromJson(Map<String, dynamic> json) {
    String readString(String key, String fallback) {
      final value = json[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
      return fallback;
    }

    return AiBreathingCoach(
      inhale: readString('inhale', 'Inhale'),
      hold: readString('hold', 'Hold'),
      exhale: readString('exhale', 'Exhale'),
    );
  }

  static const fallback = AiBreathingCoach(
    inhale: 'Inhale',
    hold: 'Hold',
    exhale: 'Exhale',
  );
}

class AiBreathingCoachService {
  const AiBreathingCoachService._();

  static Future<AiBreathingCoach> generateCoach({
    required String apiKey,
    required String mood,
  }) async {
    if (apiKey.trim().isEmpty) {
      debugPrint('AiBreathingCoachService: OPENAI_API_KEY is missing.');
      return AiBreathingCoach.fallback;
    }

    try {
      final response = await http.post(
        Uri.parse('https://api.openai.com/v1/chat/completions'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $apiKey',
        },
        body: jsonEncode({
          'model': 'gpt-4o-mini',
          'response_format': {'type': 'json_object'},
          'messages': [
            {
              'role': 'system',
              'content':
                  'You are a calm breathing coach for a wellness app. '
                      'Return only valid JSON with exactly 3 short string fields: '
                      'inhale, hold, exhale. Keep each line under 8 words.'
            },
            {
              'role': 'user',
              'content':
                  'The user currently feels: $mood. '
                      'Create soothing breathing cue text.'
            },
          ],
          'temperature': 0.6,
          'max_tokens': 80,
        }),
      );

      if (response.statusCode < 200 || response.statusCode >= 300) {
        debugPrint(
          'AiBreathingCoachService failed: ${response.statusCode} ${response.body}',
        );
        return AiBreathingCoach.fallback;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final choices = data['choices'];
      if (choices is! List || choices.isEmpty) {
        return AiBreathingCoach.fallback;
      }

      final message = choices.first['message'];
      if (message is! Map<String, dynamic>) {
        return AiBreathingCoach.fallback;
      }

      final content = message['content'];
      if (content is! String || content.trim().isEmpty) {
        return AiBreathingCoach.fallback;
      }

      final parsed = jsonDecode(content);
      if (parsed is! Map<String, dynamic>) {
        return AiBreathingCoach.fallback;
      }

      return AiBreathingCoach.fromJson(parsed);
    } catch (e) {
      debugPrint('AiBreathingCoachService exception: $e');
      return AiBreathingCoach.fallback;
    }
  }
}
