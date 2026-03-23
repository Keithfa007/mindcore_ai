import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Stores lightweight "before/after" reset metrics for v1.
/// Used for weekly insights ("Breathing helped you lower stress by X on average").
///
/// Storage: SharedPreferences key 'reset_metrics_v1' -> JSON list of entries.
class ResetMetricsService {
  static const String _kKey = 'reset_metrics_v1';

  /// Log one reset session delta.
  static Future<void> log({
    required DateTime timestamp,
    required int beforeStress, // 1..10
    required int afterStress,  // 1..10
    String? moodLabel,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final list = await _readList(prefs);

    final entry = <String, dynamic>{
      'ts': timestamp.toIso8601String(),
      'before': beforeStress.clamp(1, 10),
      'after': afterStress.clamp(1, 10),
      if (moodLabel != null && moodLabel.trim().isNotEmpty) 'mood': moodLabel.trim(),
    };

    list.add(entry);

    // Keep it light (last 180 entries)
    if (list.length > 180) {
      list.removeRange(0, list.length - 180);
    }

    await prefs.setString(_kKey, jsonEncode(list));
  }

  /// Returns summary for last [days] (default 7).
  static Future<ResetSummary> summary({int days = 7}) async {
    final prefs = await SharedPreferences.getInstance();
    final list = await _readList(prefs);

    final since = DateTime.now().subtract(Duration(days: days));
    final recent = list.where((e) {
      final ts = DateTime.tryParse((e['ts'] ?? '').toString());
      return ts != null && ts.isAfter(since);
    }).toList();

    if (recent.isEmpty) return const ResetSummary(count: 0, avgDelta: 0);

    final deltas = recent.map((e) {
      final b = (e['before'] ?? 0) as int;
      final a = (e['after'] ?? 0) as int;
      return (b - a).clamp(-10, 10);
    }).toList();

    final avg = deltas.reduce((x, y) => x + y) / deltas.length;
    return ResetSummary(count: recent.length, avgDelta: avg);
  }

  /// Export as JSON string (for v1 simple export flows).
  static Future<String> exportJson() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kKey) ?? '[]';
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kKey);
  }

  static Future<List<Map<String, dynamic>>> _readList(SharedPreferences prefs) async {
    final raw = prefs.getString(_kKey);
    if (raw == null || raw.trim().isEmpty) return <Map<String, dynamic>>[];
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! List) return <Map<String, dynamic>>[];
      return decoded.whereType<Map>().map((m) => m.cast<String, dynamic>()).toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }
}

class ResetSummary {
  final int count;
  final double avgDelta; // (before - after) average

  const ResetSummary({
    required this.count,
    required this.avgDelta,
  });
}
