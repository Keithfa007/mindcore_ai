import 'package:shared_preferences/shared_preferences.dart';

/// Centralized local data controls (v1).
/// We avoid prefs.clear() to not accidentally wipe auth/remote config flags.
/// Instead we remove known keys/prefixes used by MindReset AI's local storage.
class DataPrivacyService {
  static const List<String> _explicitKeys = [
    // Journal / mood / daily content
    'journal_entries',
    'daily_affirmation',
    'affirmation_date',
    'daily_tip_text_v3',
    'daily_tip_day_v3',
    'daily_plan_day_v3',
    'daily_plan_payload_v3',
    // TTS prefs
    'tts_enabled',
    'tts_mood_adaptive',
    'tts_speed',
    // Daily goals
    'daily_goals_remaining',
    'daily_goals_target',
    'daily_goals_last_reset_ymd',

    // Reset metrics
    'reset_metrics_v1',
  ];

  static const List<String> _prefixKeys = [
    'chat_history_',
    'chat_conversations_',
    'chat_conversations_index',
  ];

  /// Deletes MindCore AI local data (chat history, journal, daily cached content, reset metrics).
  static Future<void> deleteAllLocalMindResetData() async {
    final prefs = await SharedPreferences.getInstance();
    final keys = prefs.getKeys();

    // Remove explicit keys
    for (final k in _explicitKeys) {
      if (keys.contains(k)) {
        await prefs.remove(k);
      }
    }

    // Remove prefixes and known chat keys
    for (final k in keys) {
      if (k == 'chat_conversations_index') {
        await prefs.remove(k);
        continue;
      }
      for (final prefix in _prefixKeys) {
        if (prefix.endsWith('_')) {
          if (k.startsWith(prefix)) {
            await prefs.remove(k);
            break;
          }
        }
      }
    }
  }
}
