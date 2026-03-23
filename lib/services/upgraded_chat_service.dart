import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'model_router.dart';
import 'persona_manager.dart';
import 'proactive_suggestions.dart';

class ChatReplyBundle {
  final String reply;
  final List<String> suggestions;
  final String modelUsed;

  ChatReplyBundle({
    required this.reply,
    required this.suggestions,
    required this.modelUsed,
  });
}

class UpgradedChatService {
  final String apiKey;

  UpgradedChatService({required this.apiKey});

  Future<ChatReplyBundle> sendMessage({
    required String userMessage,
    String? currentMood,
    String? userName,
  }) async {
    final model = ModelRouter.chooseModel(userMessage);
    final personaPrompt = PersonaManager.buildPrompt(
      currentMood: currentMood,
      userName: userName,
    );

    final uri = Uri.parse('https://api.openai.com/v1/chat/completions');

    final payload = {
      'model': model,
      'messages': [
        {
          'role': 'system',
          'content': personaPrompt,
        },
        {
          'role': 'user',
          'content': userMessage,
        },
      ],
      'temperature': 0.8,
      'max_tokens': 350,
    };

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $apiKey',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'AI request failed (${response.statusCode}): ${response.body}',
      );
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final choices = data['choices'] as List<dynamic>?;

    if (choices == null || choices.isEmpty) {
      throw Exception('No AI response returned.');
    }

    final message = choices.first['message'] as Map<String, dynamic>?;
    final content = message?['content']?.toString().trim();

    if (content == null || content.isEmpty) {
      throw Exception('AI returned an empty response.');
    }

    final quickSuggestions = ProactiveSuggestions.suggestions(userMessage);

    return ChatReplyBundle(
      reply: content,
      suggestions: quickSuggestions,
      modelUsed: model,
    );
  }
}
