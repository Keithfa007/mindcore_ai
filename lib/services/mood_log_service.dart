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

class MoodLogService {
  static const String _historyKey = 'mood_history_entries_v1';

  static Future<bool> logMood({
    required String emoji,
    required String label,
    String note = '',
    DateTime? timestamp,
  }) async {
    final when  = timestamp ?? DateTime.now();
    final score = _scoreFromLabel(label);

    dev.log('MoodLogService.logMood: $emoji $label score=$score');

    await MoodRepo.instance.add(score, when: when);

    final prefs = await SharedPreferences.getInstance();
    final key   = _metaKeyForDate(when);
    await prefs.setString(key, jsonEncode({'emoji': emoji, 'label': label, 'note': note}));

    await _appendHistoryEntry(
        emoji: emoji, label: label, note: note, timestamp: when);

    try {
      await MoodFirestoreService.instance.logMoodV2(
        emoji: emoji, label: label, score: score,
        note: note.isEmpty ? null : note, timestamp: when,
      );
      return true;
    } catch (e) {
      dev.log('Firestore mood write FAILED: $e');
      return false;
    }
  }

  static Future<void> syncFromFirestore({int limit = 200}) async {
    try {
      final remote = await MoodFirestoreService.instance.getRecentMoods(limit: limit);
      if (remote.isEmpty) return;

      final entries      = <MoodEntry>[];
      final historyList  = <Map<String, dynamic>>[];
      final prefs        = await SharedPreferences.getInstance();

      for (final m in remote) {
        final tsAny = m['timestamp'];
        final when  = tsAny is Timestamp ? tsAny.toDate() : DateTime.now();
        final scoreAny = m['score'];
        final score = (scoreAny is num ? scoreAny.toInt() : 3).clamp(1, 5);
        final id    = (m['id'] ?? '').toString().isNotEmpty
            ? (m['id'] ?? '').toString()
            : when.millisecondsSinceEpoch.toString();

        entries.add(MoodEntry(id: id, timestamp: when, score: score));

        final emoji = (m['emoji'] ?? '').toString();
        final label = (m['label'] ?? '').toString();
        final note  = (m['note']  ?? '').toString();

        if (emoji.isNotEmpty || label.isNotEmpty) {
          await prefs.setString(_metaKeyForDate(when),
              jsonEncode({'emoji': emoji, 'label': label, 'note': note}));
        }

        historyList.add({
          'ts':    when.toIso8601String(),
          'emoji': emoji.isEmpty ? '\ud83d\ude42' : emoji,
          'mood':  label.isEmpty ? 'Okay' : label,
          'note':  note,
        });
      }

      entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
      await MoodRepo.instance.replaceAll(entries);

      historyList.sort((a, b) =>
          (b['ts'] as String).compareTo(a['ts'] as String));
      await prefs.setString(_historyKey, jsonEncode(historyList));
    } catch (e) {
      dev.log('Firestore → local mood sync failed: $e');
    }
  }

  static Future<Map<String, String>> todayMeta() async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(_metaKeyForDate(DateTime.now()));
    if (raw == null || raw.isEmpty) return {};
    final Map<String, dynamic> j = jsonDecode(raw);
    return {
      'emoji': (j['emoji'] ?? '').toString(),
      'label': (j['label'] ?? '').toString(),
      'note':  (j['note']  ?? '').toString(),
    };
  }

  static Future<List<double>> last7Normalized() =>
      MoodRepo.instance.last7Normalized();

  static String _metaKeyForDate(DateTime d) =>
      'mood_meta_${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static Future<void> _appendHistoryEntry({
    required String emoji,
    required String label,
    required String note,
    required DateTime timestamp,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(_historyKey);
    final list  = <Map<String, dynamic>>[];
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
      'ts':    timestamp.toIso8601String(),
      'emoji': emoji,
      'mood':  label,
      'note':  note,
    });
    await prefs.setString(_historyKey, jsonEncode(list));
  }

  // ── Score mapping ──────────────────────────────────────────────────────────
  // Maps mood labels to 1–5 score for charting and pattern detection.
  // Scores are intentionally generous so hopeful states show progress.

  static int _scoreFromLabel(String label) {
    switch (label.toLowerCase().trim()) {
      // 5 — thriving
      case 'amazing':   return 5;
      case 'grateful':  return 5;
      // 4 — doing well
      case 'happy':     return 4;
      case 'peaceful':  return 4;
      case 'calm':      return 4;
      case 'motivated': return 4;
      case 'good':      return 4;
      case 'better':    return 4;
      // 3 — okay / neutral
      case 'okay':      return 3;
      case 'neutral':   return 3;
      case 'tired':     return 3;
      case 'unsettled': return 3;
      case 'meh':       return 3;
      // 2 — struggling
      case 'sad':        return 2;
      case 'anxious':    return 2;
      case 'frustrated': return 2;
      case 'tearful':    return 2;
      case 'numb':       return 2;
      case 'low':        return 2;
      case 'stressed':   return 2;
      case 'angry':      return 2;
      // 1 — really struggling
      case 'overwhelmed': return 1;
      case 'hopeless':    return 1;
      case 'awful':       return 1;
      case 'terrible':    return 1;
      case 'panic':       return 1;
      default:            return 3;
    }
  }
}
