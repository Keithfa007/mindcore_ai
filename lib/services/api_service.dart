// lib/services/api_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mindcore_ai/env/env.dart';

/// Thin OpenAI helper for simple one-shot calls (system + user).
class ApiService {
  // Read from: --dart-define-from-file=env.dev or env.prod (via Env.openaiKey)
  static const String _apiKey = Env.openaiKey;

  static const String _endpoint =
      'https://api.openai.com/v1/chat/completions';

  // Single main model for tips etc.
  static const String _model = 'gpt-4o-mini';

  static Future<String> singleTurn({
    required String system,
    required String user,
    double temperature = 0.5,
    int maxTokens = 200,
  }) async {
    if (_apiKey.isEmpty) {
      // No key configured – caller can show a friendly fallback.
      return '';
    }

    final uri = Uri.parse(_endpoint);

    final body = jsonEncode({
      'model': _model,
      'messages': [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user},
      ],
      'temperature': temperature,
      'max_tokens': maxTokens,
    });

    try {
      final res = await http.post(
        uri,
        headers: {
          'Authorization': 'Bearer $_apiKey',
          'Content-Type': 'application/json',
        },
        body: body,
      );

      if (res.statusCode != 200) {
        // print('ApiService error: ${res.statusCode} ${res.body}');
        return '';
      }

      final data = jsonDecode(res.body) as Map<String, dynamic>;
      final choices = data['choices'] as List?;
      final text =
      choices?.first['message']?['content'] as String?;

      return text?.trim() ?? '';
    } catch (_) {
      return '';
    }
  }
}
