import 'dart:convert';
import 'dart:developer' as dev;

import 'package:shared_preferences/shared_preferences.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:mindcore_ai/services/mood_firestore_service.dart';

/// Raw entry stored for charting (score 1..5 only)
class MoodEntry {
  final String id;
  final DateTime timestamp;
  final int score; // 1..5

  MoodEntry({required this.id, required this.timestamp, required this.score});

  Map<String, dynamic> toJson() => {
    'id': id,
    'ts': timestamp.toIso8601String(),
    'score': score,
  };

  factory MoodEntry.fromJson(Map<String, dynamic> j) => MoodEntry(
    id: (j['id'] ?? '').toString(),
    timestamp: DateTime.tryParse(j['ts']?.toString() ?? '') ?? DateTime.now(),
    score: int.tryParse(j['score']?.toString() ?? '')?.clamp(1, 5) ?? 3,
  );
}

/// Storage for simple mood timeseries (used by Weekly Mood)
class MoodRepo {
  static const _key = 'mood_entries_v1';
  MoodRepo._();
  static final MoodRepo instance = MoodRepo._();

  Future<List<MoodEntry>> fetchAll() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List) return [];
    final out = <MoodEntry>[];
    for (final e in decoded) {
      if (e is Map) {
        out.add(MoodEntry.fromJson(Map<String, dynamic>.from(e)));
      }
    }
    out.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return out;
  }

  Future<void> add(int score, {DateTime? when}) async {
    final prefs = await SharedPreferences.getInstance();
    final all = await fetchAll();
    all.insert(
      0,
      MoodEntry(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        timestamp: when ?? DateTime.now(),
        score: score.clamp(1, 5),
      ),
    );
    await prefs.setString(_key, jsonEncode(all.map((e) => e.toJson()).toList()));
  }

  /// Replace local cache with a provided list (used by Firestore sync).
  Future<void> replaceAll(List<MoodEntry> entries) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode(entries.map((e) => e.toJson()).toList()),
    );
  }

  /// Returns 7 values (oldest→newest), normalized 0..1. Empty days = 0.
  Future<List<double>> last7Normalized() async {
    final all = await fetchAll();
    final today = DateTime.now();
    final startOfToday = DateTime(today.year, today.month, today.day);

    final result = <double>[];
    for (int i = 6; i >= 0; i--) {
      final day = startOfToday.subtract(Duration(days: i));
      final next = day.add(const Duration(days: 1));
      final dayEntries = all.where(
            (e) => !e.timestamp.isBefore(day) && e.timestamp.isBefore(next),
      );
      if (dayEntries.isEmpty) {
        result.add(0.0);
      } else {
        final avg = dayEntries.map((e) => e.score).reduce((a, b) => a + b) / dayEntries.length;
        result.add((avg / 5.0).clamp(0.0, 1.0));
      }
    }
    return result;
  }
}

/// Compatibility layer so this call compiles:
/// final ok = await MoodLogService.logMood(...);
class MoodLogService {
  // ✅ ADDED: list store used by MoodHistoryScreen (emoji/label/note history)
  static const String _historyKey = 'mood_history_entries_v1';

  /// Save a mood with metadata, map to a 1..5 score for charts.
  /// Returns true if Firestore sync succeeded, false otherwise.
  static Future<bool> logMood({
    required String emoji,
    required String label,
    String note = '',
    DateTime? timestamp,
  }) async {
    final when = timestamp ?? DateTime.now();
    final score = _scoreFromEmojiOrLabel(emoji, label);

    dev.log('MoodLogService.logMood called: $emoji $label score=$score note="$note"');

    // 1) Save numeric score for charts (local)
    await MoodRepo.instance.add(score, when: when);

    // 2) Save metadata locally (emoji/label/note) keyed by day
    final prefs = await SharedPreferences.getInstance();
    final key = _metaKeyForDate(when);
    final meta = {'emoji': emoji, 'label': label, 'note': note};
    await prefs.setString(key, jsonEncode(meta));

    // ✅ 2.5) ALSO append to the history list store (for MoodHistoryScreen logs)
    await _appendHistoryEntry(
      emoji: emoji,
      label: label,
      note: note,
      timestamp: when,
    );

    // 3) Sync to Firestore (cloud) - best effort
    try {
      dev.log('Attempting Firestore mood write...');
      await MoodFirestoreService.instance.logMoodV2(
        emoji: emoji,
        label: label,
        score: score,
        note: note.isEmpty ? null : note,
        timestamp: when,
      );
      dev.log('Firestore mood write OK');
      return true;
    } catch (e) {
      dev.log('Firestore mood write FAILED: $e');
      return false;
    }
  }

  /// Pull recent moods from Firestore and replace local cache (offline-first sync).
  /// Call this after login.
  static Future<void> syncFromFirestore({int limit = 200}) async {
    try {
      dev.log('Syncing moods from Firestore...');
      final remote = await MoodFirestoreService.instance.getRecentMoods(limit: limit);

      if (remote.isEmpty) {
        dev.log('No remote moods found.');
        return;
      }

      // Build chart entries (score + timestamp)
      final entries = <MoodEntry>[];
      final prefs = await SharedPreferences.getInstance();

      // ✅ Also rebuild the mood_history_entries_v1 list from remote (so logs match after sync)
      final historyList = <Map<String, dynamic>>[];

      for (final m in remote) {
        final tsAny = m['timestamp'];
        final when = tsAny is Timestamp ? tsAny.toDate() : DateTime.now();

        final scoreAny = m['score'];
        final score = (scoreAny is num ? scoreAny.toInt() : 3).clamp(1, 5);

        final id = (m['id'] ?? '').toString().isNotEmpty
            ? (m['id'] ?? '').toString()
            : when.millisecondsSinceEpoch.toString();

        entries.add(MoodEntry(
          id: id,
          timestamp: when,
          score: score,
        ));

        // Restore metadata per day (emoji/label/note)
        final emoji = (m['emoji'] ?? '').toString();
        final label = (m['label'] ?? '').toString();
        final note = (m['note'] ?? '').toString();

        if (emoji.isNotEmpty || label.isNotEmpty || note.isNotEmpty) {
          final key = _metaKeyForDate(when);
          final meta = {'emoji': emoji, 'label': label, 'note': note};
          await prefs.setString(key, jsonEncode(meta));
        }

        // ✅ Build history entry
        historyList.add({
          'ts': when.toIso8601String(),
          'emoji': emoji.isEmpty ? '🙂' : emoji,
          'mood': label.isEmpty ? 'Neutral' : label,
          'note': note,
        });
      }

      // Store newest-first like fetchAll() expects
      entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      await MoodRepo.instance.replaceAll(entries);

      // ✅ Store history list (newest-first)
      historyList.sort((a, b) => (b['ts'] as String).compareTo(a['ts'] as String));
      await prefs.setString(_historyKey, jsonEncode(historyList));

      dev.log('Firestore → local mood sync complete. Entries: ${entries.length}');
    } catch (e) {
      dev.log('Firestore → local mood sync failed: $e');
    }
  }

  /// Get today’s metadata back (emoji/label/note).
  static Future<Map<String, String>> todayMeta() async {
    final prefs = await SharedPreferences.getInstance();
    final key = _metaKeyForDate(DateTime.now());
    final raw = prefs.getString(key);
    if (raw == null || raw.isEmpty) return {};
    final Map<String, dynamic> j = jsonDecode(raw);
    return {
      'emoji': (j['emoji'] ?? '').toString(),
      'label': (j['label'] ?? '').toString(),
      'note': (j['note'] ?? '').toString(),
    };
  }

  /// Forwarder so Home can also call MoodLogService.last7Normalized()
  static Future<List<double>> last7Normalized() => MoodRepo.instance.last7Normalized();

  // ---- helpers ----
  static String _metaKeyForDate(DateTime d) =>
      'mood_meta_${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  // ✅ ADDED: append to mood_history_entries_v1
  static Future<void> _appendHistoryEntry({
    required String emoji,
    required String label,
    required String note,
    required DateTime timestamp,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_historyKey);

    final list = <Map<String, dynamic>>[];
    if (raw != null && raw.isNotEmpty) {
      try {
        final decoded = jsonDecode(raw);
        if (decoded is List) {
          for (final e in decoded) {
            if (e is Map) list.add(Map<String, dynamic>.from(e));
          }
        }
      } catch (_) {}
    }

    list.add({
      'ts': timestamp.toIso8601String(),
      'emoji': emoji,
      'mood': label,
      'note': note,
    });

    await prefs.setString(_historyKey, jsonEncode(list));
  }

  static int _scoreFromEmojiOrLabel(String emoji, String label) {
    final byEmoji = <String, int>{
      // very low
      '😞': 1, '😢': 1, '😭': 1,

      // low / stressed / panic / frustrated
      '😰': 2, '😟': 2, '😕': 2, '☹️': 2, '😠': 2, '😡': 2,

      // neutral / tired
      '😐': 3, '😶': 3, '😴': 3, '🙂': 3,

      // good
      '😊': 4, '😀': 4,

      // great
      '😄': 5, '😁': 5, '🤩': 5, '😍': 5,
    };

    final byLabel = <String, int>{
      // 1
      'awful': 1, 'terrible': 1, 'very low': 1,

      // 2
      'bad': 2, 'low': 2, 'sad': 2, 'anxious': 2, 'panic': 2,
      'frustrated': 2, 'stressed': 2,

      // 3
      'okay': 3, 'neutral': 3, 'meh': 3, 'tired': 3,

      // 4
      'good': 4, 'better': 4, 'calm': 4,

      // 5
      'great': 5, 'excellent': 5, 'amazing': 5,
    };

    final e = byEmoji[emoji];
    if (e != null) return e;

    final l = byLabel[label.trim().toLowerCase()];
    return l ?? 3;
  }

}
