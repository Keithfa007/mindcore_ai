import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/services/openai_tts_service.dart';

class AffirmationService {
  static const _apiKey = String.fromEnvironment('OPENAI_API_KEY', defaultValue: '');
  static const _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const _model = 'gpt-4o-mini';

  static Future<String> getDailyAffirmation({
    bool force = false,
    String moodLabel = 'neutral',
    bool speak = true,
    TtsSurface surface = TtsSurface.dailyMotivation,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());

    Future<void> maybeSpeakText(String text) async {
      if (!speak || !OpenAiTtsService.instance.enabled) return;
      await OpenAiTtsService.instance.speak(
        text,
        moodLabel: moodLabel,
        surface: surface,
        messageId: 'affirmation_$today',
      );
    }

    if (!force) {
      final savedDate = prefs.getString('affirmation_date');
      final saved = prefs.getString('daily_affirmation');
      if (savedDate == today && saved != null && saved.isNotEmpty) {
        await maybeSpeakText(saved);
        return saved;
      }
    }

    if (_apiKey.isEmpty) {
      const fallback = 'I choose calm, steady confidence, and kindness toward myself today.';
      await _cache(prefs, today, fallback);
      await maybeSpeakText(fallback);
      return fallback;
    }

    const prompt = 'Write one short, first-person daily affirmation (16 words max). Tone: calm, reassuring, supportive. No emojis. No quotation marks.';

    try {
      final res = await http.post(
        Uri.parse(_endpoint),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_apiKey',
        },
        body: jsonEncode({
          'model': _model,
          'messages': [
            {
              'role': 'system',
              'content': 'You are a calm, compassionate wellness coach.',
            },
            {
              'role': 'user',
              'content': prompt,
            },
          ],
          'temperature': 0.7,
        }),
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final text = (data['choices']?[0]?['message']?['content'] as String?)?.trim();
        final affirmation = (text == null || text.isEmpty)
            ? 'I am grounded, safe, and capable of gentle progress today.'
            : text;
        await _cache(prefs, today, affirmation);
        await maybeSpeakText(affirmation);
        return affirmation;
      }

      const fallback = 'I am grounded, safe, and capable of gentle progress today.';
      await _cache(prefs, today, fallback);
      await maybeSpeakText(fallback);
      return fallback;
    } catch (_) {
      const fallback = 'I choose calm and kindness toward myself today.';
      await _cache(prefs, today, fallback);
      await maybeSpeakText(fallback);
      return fallback;
    }
  }

  static Future<void> _cache(SharedPreferences prefs, String date, String text) async {
    await prefs.setString('daily_affirmation', text);
    await prefs.setString('affirmation_date', date);
  }
}
