import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/services/openai_tts_service.dart';

class DailyTipService {
  static const _kTipTextKey = 'daily_tip_text_v3';
  static const _kTipDayKey = 'daily_tip_day_v3';
  static const _kTipSpokenDayKey = 'daily_tip_spoken_day_v1';

  static const _apiKey =
      String.fromEnvironment('OPENAI_API_KEY', defaultValue: '');
  static const _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const _model = 'gpt-4o-mini';

  static Future<String> getDailyTip({
    bool forceRefresh = false,
    bool speak = false,
    String moodLabel = 'calm',
    TtsSurface surface = TtsSurface.recommendation,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final todayKey = _yyyyMMdd(DateTime.now());

    if (!forceRefresh) {
      final cachedDay = prefs.getString(_kTipDayKey);
      final cachedTip = prefs.getString(_kTipTextKey);
      if (cachedDay == todayKey &&
          cachedTip != null &&
          cachedTip.trim().isNotEmpty) {
        if (speak) {
          await speakTip(
            cachedTip,
            moodLabel: moodLabel,
            surface: surface,
            messageId: 'daily_tip_$todayKey',
          );
        }
        return cachedTip;
      }
    }

    if (_apiKey.isEmpty) {
      final fallback = _offlineFallbackFor(DateTime.now());
      await _cache(prefs, todayKey, fallback);
      if (speak) {
        await speakTip(
          fallback,
          moodLabel: moodLabel,
          surface: surface,
          messageId: 'daily_tip_$todayKey',
        );
      }
      return fallback;
    }

    const prompt =
        'Give ONE concise daily mental reset tip. '
        'Tone: calm, practical, encouraging. '
        'Single sentence. Max 160 characters. '
        'No emojis. No greetings.';

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
              'content':
                  'You are a calm, grounded wellness coach focused on practical mental resets.',
            },
            {
              'role': 'user',
              'content': prompt,
            },
          ],
          'temperature': 0.5,
        }),
      );

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final text =
            (data['choices']?[0]?['message']?['content'] as String?)?.trim();

        final tip = (text == null || text.isEmpty)
            ? _offlineFallbackFor(DateTime.now())
            : _sanitize(text);

        await _cache(prefs, todayKey, tip);
        if (speak) {
          await speakTip(
            tip,
            moodLabel: moodLabel,
            surface: surface,
            messageId: 'daily_tip_$todayKey',
          );
        }
        return tip;
      }

      final fallback = _offlineFallbackFor(DateTime.now());
      await _cache(prefs, todayKey, fallback);
      if (speak) {
        await speakTip(
          fallback,
          moodLabel: moodLabel,
          surface: surface,
          messageId: 'daily_tip_$todayKey',
        );
      }
      return fallback;
    } catch (_) {
      final fallback = _offlineFallbackFor(DateTime.now());
      await _cache(prefs, todayKey, fallback);
      if (speak) {
        await speakTip(
          fallback,
          moodLabel: moodLabel,
          surface: surface,
          messageId: 'daily_tip_$todayKey',
        );
      }
      return fallback;
    }
  }

  static Future<bool> speakTip(
    String text, {
    String moodLabel = 'calm',
    TtsSurface surface = TtsSurface.recommendation,
    String? messageId,
    bool force = true,
  }) async {
    final cleaned = _sanitize(text);
    if (cleaned.isEmpty) return false;
    final resolvedMessageId = messageId ?? 'daily_tip_${cleaned.hashCode}';
    return OpenAiTtsService.instance.speak(
      cleaned,
      moodLabel: moodLabel,
      surface: surface,
      messageId: resolvedMessageId,
      force: force,
    );
  }

  static Future<void> maybeSpeakOncePerDay({
    String moodLabel = 'calm',
  }) async {
    if (!OpenAiTtsService.instance.enabled) return;
    if (!await OpenAiTtsService.instance.getSurfaceEnabled(TtsSurface.recommendation)) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final todayKey = _yyyyMMdd(DateTime.now());
    final last = prefs.getString(_kTipSpokenDayKey);
    if (last == todayKey) return;

    final tip = await getDailyTip(forceRefresh: false);
    await prefs.setString(_kTipSpokenDayKey, todayKey);
    await speakTip(
      tip,
      moodLabel: moodLabel,
      surface: TtsSurface.recommendation,
      messageId: 'daily_tip_$todayKey',
    );
  }

  static Future<void> _cache(
    SharedPreferences prefs,
    String dayKey,
    String text,
  ) async {
    await prefs.setString(_kTipDayKey, dayKey);
    await prefs.setString(_kTipTextKey, text);
  }

  static String _yyyyMMdd(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

  static String _sanitize(String s) => s
      .replaceAll('\n', ' ')
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();

  static String _offlineFallbackFor(DateTime when) {
    final base = DateTime(2024, 1, 1);
    final days = when.difference(base).inDays.abs();
    final idx = days % _fallbackTips.length;
    return _fallbackTips[idx];
  }

  static Future<void> invalidateCache() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kTipTextKey);
    await prefs.remove(_kTipDayKey);
    await prefs.remove(_kTipSpokenDayKey);
  }

  static const List<String> _fallbackTips = [
    'Inhale slowly through your nose, exhale longer than you inhale.',
    'Relax your shoulders and unclench your jaw.',
    'Do one small thing fully present.',
    'Drink a glass of water and pause for three breaths.',
    'Step outside and notice one sound.',
    'Single-task for the next 10 minutes.',
    'Put your phone face down and breathe once.',
    'Stretch your neck gently side to side.',
    'Name one thing you can let go of today.',
    'Check in: hungry, tired, tense? Address one.',
    'Slow down your next movement.',
    'Write one sentence about how you feel.',
    'Progress matters more than perfection today.',
    'Pause before your next reaction.',
    'Ground your feet and feel the floor.',
  ];
}
