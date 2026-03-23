import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/services/affirmation_service.dart';
import 'package:mindcore_ai/services/daily_tip_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

class DailyMotivationService {
  static const String _kLastSpokenYmd = 'daily_motivation_last_spoken_ymd_v1';

  static String _ymd(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

  static Future<void> maybeSpeakOnAppOpen({
    String moodLabel = 'neutral',
  }) async {
    if (!OpenAiTtsService.instance.enabled) return;
    if (!await OpenAiTtsService.instance.getSurfaceEnabled(TtsSurface.dailyMotivation)) {
      return;
    }

    final prefs = await SharedPreferences.getInstance();
    final today = _ymd(DateTime.now());
    final last = prefs.getString(_kLastSpokenYmd);
    if (last == today) return;

    await prefs.setString(_kLastSpokenYmd, today);
    await AffirmationService.getDailyAffirmation(
      force: false,
      moodLabel: moodLabel,
      speak: true,
      surface: TtsSurface.dailyMotivation,
    );
    await DailyTipService.maybeSpeakOncePerDay(moodLabel: moodLabel);
  }
}
