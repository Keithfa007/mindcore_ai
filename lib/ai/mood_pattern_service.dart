// lib/ai/mood_pattern_service.dart
//
// AI-powered mood pattern detection.
// Uses gpt-4o-mini with real data: mood history, journal entries,
// and recent chat messages. Cached once per day. Returns null if
// there is not enough genuine data to say anything meaningful.

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';
import 'package:mindcore_ai/pages/helpers/chat_persistence.dart';
import 'package:mindcore_ai/env/env.dart';

/// A detected mood pattern with headline, detail and optional action.
class MoodPrediction {
  final String headline;
  final String detail;
  final IconData icon;
  final Color accentColor;
  final String? actionLabel;
  final String? actionRoute;

  const MoodPrediction({
    required this.headline,
    required this.detail,
    required this.icon,
    required this.accentColor,
    this.actionLabel,
    this.actionRoute,
  });
}

class MoodPatternService {
  static const _kCache     = 'mood_pattern_v3';
  static const _kCacheDate = 'mood_pattern_date_v3';

  // In-memory cache
  static String? _mem;
  static String? _memDate;

  // ── Public API ───────────────────────────────────────────────────

  static Future<MoodPrediction?> detect() async {
    final all = await MoodRepo.instance.fetchAll();

    // Need at least 7 real mood logs before we say anything
    if (all.length < 7) return null;

    final now   = DateTime.now();
    final today = _dateKey(now);

    // In-memory hit
    if (_memDate == today && _mem != null) {
      return _decode(_mem!);
    }

    // SharedPreferences hit
    final prefs = await SharedPreferences.getInstance();
    if (prefs.getString(_kCacheDate) == today) {
      final cached = prefs.getString(_kCache);
      if (cached != null && cached.isNotEmpty) {
        _mem     = cached;
        _memDate = today;
        return _decode(cached);
      }
    }

    // Build real context and call AI
    final ctx = await _buildContext(all, now);
    MoodPrediction? result;
    try {
      result = await _callAI(ctx, now);
    } catch (_) {
      // AI unavailable — fall back to strict math
      result = _mathFallback(all, now);
    }

    // Cache (even null — as empty string sentinel — to avoid repeated calls)
    final encoded = result != null ? _encode(result) : '';
    _mem     = encoded;
    _memDate = today;
    await prefs.setString(_kCache, encoded);
    await prefs.setString(_kCacheDate, today);

    return result;
  }

  /// Force refresh — call after new mood log or journal entry.
  static Future<MoodPrediction?> refresh() async {
    _mem     = null;
    _memDate = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kCache);
    await prefs.remove(_kCacheDate);
    return detect();
  }

  // ── Context builder ───────────────────────────────────────────────

  static Future<Map<String, dynamic>> _buildContext(
      List<MoodEntry> all, DateTime now) async {
    final cutoff = now.subtract(const Duration(days: 28));
    final recent = all
        .where((e) => e.timestamp.isAfter(cutoff))
        .toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

    // Mood entries — score only (MoodEntry has no label field)
    final moodLines = recent.take(20).map((e) {
      final d   = e.timestamp;
      final dow = _dowName(d.weekday);
      return '$dow ${d.day}/${d.month}: score=${e.score}/5';
    }).toList();

    // Day-of-week averages for today
    final todayDow       = now.weekday;
    final sameDowEntries = all
        .where((e) => e.timestamp.weekday == todayDow)
        .toList();
    final todayDowAvg = sameDowEntries.isEmpty
        ? null
        : sameDowEntries.map((e) => e.score).reduce((a, b) => a + b) /
            sameDowEntries.length;
    final overallAvg = all.isEmpty
        ? null
        : all.map((e) => e.score).reduce((a, b) => a + b) / all.length;

    // Journal snippets — last 3 entries, 120 chars each
    final journalLines = <String>[];
    try {
      final entries = await JournalService.getEntries();
      for (final e in entries.take(3)) {
        final text = e.note.trim();
        journalLines.add(text.length > 120 ? text.substring(0, 120) : text);
      }
    } catch (_) {}

    // Recent user chat messages — last 5, 80 chars each
    final chatLines = <String>[];
    try {
      final convId  = await ChatPersistence.ensureDefault();
      final msgs    = await ChatPersistence.load(convId);
      final userMsgs = msgs
          .where((m) => m.role == 'user')
          .toList()
          .reversed
          .take(5)
          .toList();
      for (final m in userMsgs) {
        final t = m.text.trim();
        chatLines.add(t.length > 80 ? t.substring(0, 80) : t);
      }
    } catch (_) {}

    return {
      'moodLines':    moodLines,
      'todayDow':     _dowName(todayDow),
      'todayDowAvg':  todayDowAvg,
      'overallAvg':   overallAvg,
      'sameDowCount': sameDowEntries.length,
      'journalLines': journalLines,
      'chatLines':    chatLines,
      'totalLogs':    all.length,
    };
  }

  // ── AI call ──────────────────────────────────────────────────────────────

  static Future<MoodPrediction?> _callAI(
      Map<String, dynamic> ctx, DateTime now) async {
    final apiKey = Env.openaiKey;
    if (apiKey.trim().isEmpty) {
      return _mathFallback(await MoodRepo.instance.fetchAll(), now);
    }

    final moodLines    = (ctx['moodLines']    as List).cast<String>();
    final todayDow     = ctx['todayDow']     as String;
    final todayDowAvg  = ctx['todayDowAvg']  as double?;
    final overallAvg   = ctx['overallAvg']   as double?;
    final sameDowCount = ctx['sameDowCount'] as int;
    final journalLines = (ctx['journalLines'] as List).cast<String>();
    final chatLines    = (ctx['chatLines']    as List).cast<String>();
    final totalLogs    = ctx['totalLogs']    as int;

    final sb = StringBuffer();
    sb.writeln(
        'You are MindCore AI. Analyse the real wellbeing data below and '
        'identify ONE genuine pattern or insight that is relevant to the user '
        'TODAY ($todayDow, ${now.day}/${now.month}/${now.year}).');
    sb.writeln();
    sb.writeln('TOTAL MOOD LOGS: $totalLogs');
    sb.writeln();

    sb.writeln('MOOD HISTORY (recent first, score 1-5):');
    for (final line in moodLines) sb.writeln('  $line');
    sb.writeln();

    if (todayDowAvg != null && overallAvg != null && sameDowCount >= 3) {
      sb.writeln(
          'TODAY IS $todayDow. Historical average for ${todayDow}s: '
          '${todayDowAvg.toStringAsFixed(1)}/5 '
          '(from $sameDowCount logs). Overall average: '
          '${overallAvg.toStringAsFixed(1)}/5.');
      sb.writeln();
    }

    if (journalLines.isNotEmpty) {
      sb.writeln('RECENT JOURNAL ENTRIES:');
      for (final line in journalLines) sb.writeln('  "$line"');
      sb.writeln();
    }

    if (chatLines.isNotEmpty) {
      sb.writeln('RECENT THINGS THE USER TYPED TO THE AI:');
      for (final line in chatLines) sb.writeln('  "$line"');
      sb.writeln();
    }

    sb.writeln('RULES:');
    sb.writeln(
        '- Only surface a pattern if it is REAL and statistically meaningful '
        '(at least 3 data points supporting it). Do not invent patterns.');
    sb.writeln(
        '- If today is historically a harder day for this user, mention that '
        'it is relevant RIGHT NOW.');
    sb.writeln(
        '- If journal or chat shows recurring emotional themes, reference them.');
    sb.writeln('- If the data shows no real pattern, return exactly: NONE');
    sb.writeln(
        '- Be warm but honest. No empty positivity. No fake encouragement.');
    sb.writeln('- headline: max 8 words');
    sb.writeln(
        '- detail: 2 sentences max, specific to the actual data, under 35 words');
    sb.writeln('- type must be one of: declining, improving, weekly_pattern, '
        'time_pattern, journal_pattern, positive');
    sb.writeln(
        '- actionRoute must be one of: /breathe, /reset, /chat, /daily-hub');
    sb.writeln();
    sb.writeln(
        'Return ONLY valid JSON (no markdown, no backticks) in this exact format:');
    sb.writeln(
        '{"headline":"...","detail":"...","type":"...","actionLabel":"...","actionRoute":"..."}');
    sb.writeln('Or return exactly: NONE');

    final response = await http
        .post(
          Uri.parse('https://api.openai.com/v1/chat/completions'),
          headers: {
            'Authorization': 'Bearer $apiKey',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({
            'model': 'gpt-4o-mini',
            'messages': [
              {'role': 'user', 'content': sb.toString()}
            ],
            'temperature': 0.3,
            'max_tokens': 120,
          }),
        )
        .timeout(const Duration(seconds: 14));

    if (response.statusCode != 200) {
      return _mathFallback(await MoodRepo.instance.fetchAll(), now);
    }

    final json    = jsonDecode(response.body) as Map<String, dynamic>;
    final choices = json['choices'] as List?;
    if (choices == null || choices.isEmpty) return null;
    final content = (choices.first as Map<String, dynamic>)['message']
            ?['content']
            ?.toString()
            .trim() ??
        '';

    if (content.toUpperCase() == 'NONE' || content.isEmpty) return null;

    try {
      final data = jsonDecode(content) as Map<String, dynamic>;
      final type  = data['type']?.toString() ?? 'weekly_pattern';
      return MoodPrediction(
        headline:    data['headline']?.toString() ?? '',
        detail:      data['detail']?.toString() ?? '',
        icon:        _iconForType(type),
        accentColor: _colorForType(type),
        actionLabel: data['actionLabel']?.toString(),
        actionRoute: data['actionRoute']?.toString(),
      );
    } catch (_) {
      return null;
    }
  }

  // ── Math fallback (strict thresholds) ────────────────────────────────
  // Only fires on very clear signals — no guessing.

  static MoodPrediction? _mathFallback(List<MoodEntry> all, DateTime now) {
    if (all.length < 7) return null;

    final byDay = <String, List<int>>{};
    for (final e in all) {
      (byDay[_dateKey(e.timestamp)] ??= []).add(e.score);
    }
    final days = byDay.keys.toList()..sort();
    if (days.length < 5) return null;

    final lastFive = days.reversed.take(5).toList().reversed.toList();
    final avgs     = lastFive
        .map((k) => byDay[k]!.reduce((a, b) => a + b) / byDay[k]!.length)
        .toList();

    // Strict 5-day declining streak
    bool declining = true;
    for (int i = 1; i < avgs.length; i++) {
      if (avgs[i] >= avgs[i - 1]) { declining = false; break; }
    }
    if (declining && avgs.last <= 2.5) {
      return const MoodPrediction(
        headline: 'Your mood has been sliding this week',
        detail:
            'The last five days show a consistent downward trend. A breathing session might help you level out.',
        icon: Icons.trending_down_rounded,
        accentColor: Color(0xFF9B7FFF),
        actionLabel: 'Try breathing',
        actionRoute: '/breathe',
      );
    }

    // Strict 5-day improving streak
    bool improving = true;
    for (int i = 1; i < avgs.length; i++) {
      if (avgs[i] <= avgs[i - 1]) { improving = false; break; }
    }
    if (improving && avgs.last >= 4.0) {
      return const MoodPrediction(
        headline: 'Five days of steady improvement',
        detail:
            "Your mood has climbed consistently over the last five days. That's real progress worth acknowledging.",
        icon: Icons.trending_up_rounded,
        accentColor: Color(0xFF32D0BE),
        actionLabel: 'Log today',
        actionRoute: '/daily-hub',
      );
    }

    return null;
  }

  // ── Type → icon / color ───────────────────────────────────────────────────

  static IconData _iconForType(String type) {
    switch (type) {
      case 'declining':       return Icons.trending_down_rounded;
      case 'improving':       return Icons.trending_up_rounded;
      case 'weekly_pattern':  return Icons.calendar_today_rounded;
      case 'time_pattern':    return Icons.wb_twilight_rounded;
      case 'journal_pattern': return Icons.auto_awesome_rounded;
      case 'positive':        return Icons.star_rounded;
      default:                return Icons.insights_rounded;
    }
  }

  static Color _colorForType(String type) {
    switch (type) {
      case 'declining':       return const Color(0xFF9B7FFF);
      case 'improving':       return const Color(0xFF32D0BE);
      case 'weekly_pattern':  return const Color(0xFF4D7CFF);
      case 'time_pattern':    return const Color(0xFF74C3FF);
      case 'journal_pattern': return const Color(0xFFE8943A);
      case 'positive':        return const Color(0xFF32D0BE);
      default:                return const Color(0xFF4D7CFF);
    }
  }

  // ── Cache helpers ────────────────────────────────────────────────────

  static String _encode(MoodPrediction p) => jsonEncode({
        'headline':    p.headline,
        'detail':      p.detail,
        'type':        _reverseType(p.icon),
        'actionLabel': p.actionLabel,
        'actionRoute': p.actionRoute,
      });

  static MoodPrediction? _decode(String raw) {
    if (raw.isEmpty) return null;
    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      final type = data['type']?.toString() ?? 'weekly_pattern';
      return MoodPrediction(
        headline:    data['headline']?.toString() ?? '',
        detail:      data['detail']?.toString() ?? '',
        icon:        _iconForType(type),
        accentColor: _colorForType(type),
        actionLabel: data['actionLabel']?.toString(),
        actionRoute: data['actionRoute']?.toString(),
      );
    } catch (_) {
      return null;
    }
  }

  static String _reverseType(IconData icon) {
    if (icon == Icons.trending_down_rounded)  return 'declining';
    if (icon == Icons.trending_up_rounded)    return 'improving';
    if (icon == Icons.calendar_today_rounded) return 'weekly_pattern';
    if (icon == Icons.wb_twilight_rounded)    return 'time_pattern';
    if (icon == Icons.auto_awesome_rounded)   return 'journal_pattern';
    if (icon == Icons.star_rounded)           return 'positive';
    return 'weekly_pattern';
  }

  // ── Utility ────────────────────────────────────────────────────────────

  static String _dateKey(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  static String _dowName(int weekday) {
    const names = [
      '', 'Monday', 'Tuesday', 'Wednesday',
      'Thursday', 'Friday', 'Saturday', 'Sunday',
    ];
    return names[weekday];
  }
}
