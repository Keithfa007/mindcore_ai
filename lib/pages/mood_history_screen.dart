// lib/pages/mood_history_screen.dart
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

import 'package:mindcore_ai/services/premium_service.dart';

const kCardShadow = Color(0x14000000);

enum HistoryTab { progress, mood }

enum ProgressRange { week, month, year }

class MoodEntry {
  final DateTime timestamp;
  final String emoji;
  final String label;
  final String note;
  final int mood;

  MoodEntry({
    required this.timestamp,
    required this.emoji,
    required this.label,
    required this.note,
    required this.mood,
  });

  static int scoreFromEmoji(String e) {
    switch (e) {
      case '😞':
      case '😢':
      case '😭':
        return 1;
      case '😟':
      case '☹️':
        return 2;
      case '😐':
      case '🙂':
        return 3;
      case '😊':
      case '😀':
        return 4;
      case '😄':
      case '😁':
      case '🤩':
      case '😍':
        return 5;
      default:
        return 3;
    }
  }

  static MoodEntry fromJson(Map<String, dynamic> j) {
    final ts = DateTime.tryParse(j['ts'] as String? ?? '') ?? DateTime.now();
    final emoji = (j['emoji'] as String?) ?? '🙂';
    final label = (j['mood'] as String?) ?? 'Neutral';
    final note = (j['note'] as String?) ?? '';
    final score = scoreFromEmoji(emoji);
    return MoodEntry(
        timestamp: ts, emoji: emoji, label: label, note: note, mood: score);
  }

  Map<String, dynamic> toJson() => {
        'ts': timestamp.toIso8601String(),
        'emoji': emoji,
        'mood': label,
        'note': note,
      };
}

class _WeeklyPoint {
  final DateTime day;
  final double avg;
  final int count;
  final List<MoodEntry> entries;

  const _WeeklyPoint({
    required this.day,
    required this.avg,
    required this.count,
    required this.entries,
  });
}

class MoodHistoryScreen extends StatefulWidget {
  final DateTime? focusDay;

  const MoodHistoryScreen({super.key, this.focusDay});

  @override
  State<MoodHistoryScreen> createState() => _MoodHistoryScreenState();
}

class _MoodHistoryScreenState extends State<MoodHistoryScreen> {
  static const _moodStoreKey = 'mood_history_entries_v1';

  final List<MoodEntry> _allEntries = [];
  bool _loadingMood = true;

  HistoryTab _tab = HistoryTab.progress;
  ProgressRange _range = ProgressRange.week;

  late DateTime _monthCursor;

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
    _monthCursor = DateTime(DateTime.now().year, DateTime.now().month, 1);
    _loadMoodFromStore();
  }

  // ✅ Premium gate: show paywall if not premium, then send user home if still not premium.
  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      if (mounted && !PremiumService.isPremium.value) {
        Navigator.of(context).pushReplacementNamed('/home');
      }
    }
  }

  Future<void> _loadMoodFromStore() async {
    setState(() => _loadingMood = true);
    final prefs = await SharedPreferences.getInstance();

    String? raw = prefs.getString(_moodStoreKey);

    if (raw == null || raw.isEmpty) {
      final maybeOld = prefs.getString('journal_entries');
      if (maybeOld != null && maybeOld.isNotEmpty) {
        try {
          final list = (jsonDecode(maybeOld) as List)
              .map((e) => Map<String, dynamic>.from(e))
              .where((m) => m.containsKey('emoji'))
              .toList();
          if (list.isNotEmpty) {
            raw = jsonEncode(list);
            await prefs.setString(_moodStoreKey, raw);
          }
        } catch (_) {}
      }
    }

    _allEntries.clear();
    if (raw != null && raw.isNotEmpty) {
      try {
        final list = (jsonDecode(raw) as List)
            .map((e) => MoodEntry.fromJson(Map<String, dynamic>.from(e)))
            .toList();
        _allEntries.addAll(list);
      } catch (_) {}
    }

    _allEntries.sort((a, b) => b.timestamp.compareTo(a.timestamp));

    if (!mounted) return;
    setState(() => _loadingMood = false);
  }

  List<MoodEntry> get _moodMonth {
    final first = DateTime(_monthCursor.year, _monthCursor.month, 1);
    final last = DateTime(_monthCursor.year, _monthCursor.month + 1, 0);
    final list = _allEntries.where((e) {
      final d = DateTime(e.timestamp.year, e.timestamp.month, e.timestamp.day);
      return !d.isBefore(first) && !d.isAfter(last);
    }).toList()
      ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return list;
  }

  double _avgMoodOf(List<MoodEntry> list) {
    if (list.isEmpty) return 0;
    final sum = list.fold<int>(0, (a, e) => a + e.mood);
    return sum / list.length;
  }

  int _bestStreakOf(List<MoodEntry> list) {
    if (list.isEmpty) return 0;
    final byDay = <String, int>{};
    for (final e in list) {
      final key = DateFormat('yyyy-MM-dd').format(e.timestamp);
      byDay[key] = (byDay[key] ?? 0) < e.mood ? e.mood : (byDay[key] ?? e.mood);
    }
    final sortedDays = byDay.keys.toList()..sort();
    final startDay = DateTime.parse(sortedDays.first);
    final endDay = DateTime.parse(sortedDays.last);
    int best = 0, run = 0;
    var d = endDay;
    while (!d.isBefore(startDay)) {
      final k = DateFormat('yyyy-MM-dd').format(d);
      if ((byDay[k] ?? 0) >= 3) {
        run++;
        if (run > best) best = run;
      } else {
        run = 0;
      }
      d = d.subtract(const Duration(days: 1));
    }
    return best;
  }

  List<_WeeklyPoint> _buildLast7Points() {
    final today = DateTime.now();
    final end = DateTime(today.year, today.month, today.day);
    final start = end.subtract(const Duration(days: 6));
    final sums = <String, double>{};
    final counts = <String, int>{};
    final byDayEntries = <String, List<MoodEntry>>{};
    for (final e in _allEntries) {
      final d = DateTime(e.timestamp.year, e.timestamp.month, e.timestamp.day);
      if (d.isBefore(start) || d.isAfter(end)) continue;
      final k = DateFormat('yyyy-MM-dd').format(d);
      sums[k] = (sums[k] ?? 0) + e.mood.toDouble();
      counts[k] = (counts[k] ?? 0) + 1;
      (byDayEntries[k] ??= <MoodEntry>[]).add(e);
    }
    final points = <_WeeklyPoint>[];
    for (int i = 0; i < 7; i++) {
      final day = start.add(Duration(days: i));
      final k = DateFormat('yyyy-MM-dd').format(day);
      final c = counts[k] ?? 0;
      final avg = c == 0 ? 0.0 : ((sums[k] ?? 0) / c);
      final entries = (byDayEntries[k] ?? <MoodEntry>[])
        ..sort((a, b) => a.timestamp.compareTo(b.timestamp));
      points.add(_WeeklyPoint(day: day, avg: avg, count: c, entries: entries));
    }
    return points;
  }

  List<_WeeklyPoint> _buildLast12MonthsPoints() {
    final now = DateTime.now();
    final points = <_WeeklyPoint>[];
    for (int i = 11; i >= 0; i--) {
      final m = DateTime(now.year, now.month - i, 1);
      double sum = 0;
      int count = 0;
      for (final e in _allEntries) {
        if (e.timestamp.year == m.year && e.timestamp.month == m.month) {
          sum += e.mood.toDouble();
          count += 1;
        }
      }
      final avg = count == 0 ? 0.0 : (sum / count);
      points.add(_WeeklyPoint(day: m, avg: avg, count: count, entries: const []));
    }
    return points;
  }

  List<_WeeklyPoint> _buildLast5YearsPoints() {
    final now = DateTime.now();
    final points = <_WeeklyPoint>[];
    for (int i = 4; i >= 0; i--) {
      final y = now.year - i;
      double sum = 0;
      int count = 0;
      for (final e in _allEntries) {
        if (e.timestamp.year == y) {
          sum += e.mood.toDouble();
          count += 1;
        }
      }
      final avg = count == 0 ? 0.0 : (sum / count);
      points.add(_WeeklyPoint(day: DateTime(y, 1, 1), avg: avg, count: count, entries: const []));
    }
    return points;
  }

  double _avgOfPoints(List<_WeeklyPoint> pts) {
    final vals = pts.where((p) => p.avg > 0).map((p) => p.avg).toList();
    if (vals.isEmpty) return 0;
    return vals.reduce((a, b) => a + b) / vals.length;
  }

  double _trendOfPoints(List<_WeeklyPoint> pts) {
    final vals = pts.where((p) => p.avg > 0).toList();
    if (vals.length < 2) return 0;
    return vals.last.avg - vals.first.avg;
  }

  String _bestLabel(List<_WeeklyPoint> pts) {
    final vals = pts.where((p) => p.avg > 0).toList();
    if (vals.isEmpty) return '—';
    vals.sort((a, b) => b.avg.compareTo(a.avg));
    return _range == ProgressRange.week
        ? DateFormat('EEE').format(vals.first.day)
        : (_range == ProgressRange.month
            ? DateFormat('MMM').format(vals.first.day)
            : DateFormat('yyyy').format(vals.first.day));
  }

  String _toughLabel(List<_WeeklyPoint> pts) {
    final vals = pts.where((p) => p.avg > 0).toList();
    if (vals.isEmpty) return '—';
    vals.sort((a, b) => a.avg.compareTo(b.avg));
    return _range == ProgressRange.week
        ? DateFormat('EEE').format(vals.first.day)
        : (_range == ProgressRange.month
            ? DateFormat('MMM').format(vals.first.day)
            : DateFormat('yyyy').format(vals.first.day));
  }

  int _entriesCount(List<_WeeklyPoint> pts) =>
      pts.fold<int>(0, (a, p) => a + p.count);

  List<Widget> _buildMoodGroupWidgets(List<MoodEntry> entries) {
    if (entries.isEmpty) return const [_EmptyState()];
    final byDay = <String, List<MoodEntry>>{};
    for (final e in entries) {
      final k = DateFormat('yyyy-MM-dd').format(e.timestamp);
      (byDay[k] ??= <MoodEntry>[]).add(e);
    }
    final keys = byDay.keys.toList()..sort((a, b) => b.compareTo(a));
    final widgets = <Widget>[];
    for (final k in keys) {
      final date = DateTime.parse(k);
      final items = byDay[k]!
        ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
      widgets
        ..add(
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
            child: Text(
              DateFormat('EEE, MMM d').format(date),
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16),
            ),
          ),
        )
        ..addAll(items.map((e) => _MoodCard(entry: e)));
    }
    return widgets;
  }

  void _showDayDetails(BuildContext context, _WeeklyPoint p) {
    final title = DateFormat('EEE, MMM d').format(p.day);
    showModalBottomSheet(
      context: context,
      showDragHandle: true,
      builder: (ctx) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                        fontWeight: FontWeight.w900, fontSize: 18)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    _pill(context, 'Avg',
                        p.avg == 0 ? '—' : p.avg.toStringAsFixed(1)),
                    const SizedBox(width: 8),
                    _pill(context, 'Logs', '${p.count}'),
                  ],
                ),
                const SizedBox(height: 12),
                if (p.entries.isEmpty)
                  const Text('No mood logs for this day.')
                else
                  ...p.entries.map((e) {
                    final time = DateFormat('HH:mm').format(e.timestamp);
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      child: Row(
                        children: [
                          Text(e.emoji, style: const TextStyle(fontSize: 20)),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              '${e.label} • $time',
                              style: const TextStyle(fontWeight: FontWeight.w700),
                            ),
                          ),
                          Text('${e.mood}/5',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                        ],
                      ),
                    );
                  }),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _pill(BuildContext context, String label, String value) {
    final theme = Theme.of(context);
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          color: theme.colorScheme.primary.withValues(alpha: 0.08),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Text('$label: $value',
            style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      title: 'History',
      bottomIndex: 5,
      body: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          children: [
            Wrap(
              spacing: 8,
              children: [
                _TopTabChip(
                  label: 'Progress',
                  selected: _tab == HistoryTab.progress,
                  onTap: () => setState(() => _tab = HistoryTab.progress),
                ),
                _TopTabChip(
                  label: 'Mood Logs',
                  selected: _tab == HistoryTab.mood,
                  onTap: () => setState(() => _tab = HistoryTab.mood),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _tab == HistoryTab.progress
                  ? _buildProgressTab(context)
                  : _buildMoodTab(context),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressTab(BuildContext context) {
    if (_loadingMood) return const Center(child: CircularProgressIndicator());
    final theme = Theme.of(context);
    final pts = _range == ProgressRange.week
        ? _buildLast7Points()
        : (_range == ProgressRange.month
            ? _buildLast12MonthsPoints()
            : _buildLast5YearsPoints());
    final avg = _avgOfPoints(pts);
    final trend = _trendOfPoints(pts);
    final best = _bestLabel(pts);
    final tough = _toughLabel(pts);
    final entries = _entriesCount(pts);
    final coverage = _range == ProgressRange.week
        ? '${pts.where((p) => p.avg > 0).length}/7 days'
        : (_range == ProgressRange.month
            ? '${pts.where((p) => p.avg > 0).length}/12 months'
            : '${pts.where((p) => p.avg > 0).length}/5 yrs');
    final labelMode = _range == ProgressRange.week
        ? _BarLabelMode.week
        : (_range == ProgressRange.month ? _BarLabelMode.month : _BarLabelMode.year);
    String title, subtitle;
    switch (_range) {
      case ProgressRange.week:
        title = 'Weekly Mood'; subtitle = 'Your last 7 days at a glance'; break;
      case ProgressRange.month:
        title = 'Monthly Mood'; subtitle = 'Last 12 months overview'; break;
      case ProgressRange.year:
        title = 'Yearly Mood'; subtitle = 'Last 5 years overview'; break;
    }
    return AnimatedBackdrop(
      child: RefreshIndicator(
        onRefresh: _loadMoodFromStore,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
          children: [
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SectionHeroCard(title: title, subtitle: subtitle),
                  const SizedBox(height: 8),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                    child: Wrap(
                      spacing: 8,
                      children: [
                        _RangeChip(label: 'Week', selected: _range == ProgressRange.week, onTap: () => setState(() => _range = ProgressRange.week)),
                        _RangeChip(label: 'Month', selected: _range == ProgressRange.month, onTap: () => setState(() => _range = ProgressRange.month)),
                        _RangeChip(label: 'Year', selected: _range == ProgressRange.year, onTap: () => setState(() => _range = ProgressRange.year)),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
                    child: _DailyMoodBars(
                      points: pts,
                      labelMode: labelMode,
                      onBarTap: _range == ProgressRange.week ? (p) => _showDayDetails(context, p) : null,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
                    child: Column(
                      children: [
                        Row(
                          children: [
                            Expanded(child: _StatTile(label: 'Average', value: avg == 0 ? '—' : avg.toStringAsFixed(1))),
                            const SizedBox(width: 10),
                            Expanded(child: _StatTile(label: 'Trend', value: trend == 0 ? '—' : (trend > 0 ? '+${trend.toStringAsFixed(1)}' : trend.toStringAsFixed(1)), icon: trend > 0 ? Icons.trending_up : (trend < 0 ? Icons.trending_down : null))),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Row(children: [Expanded(child: _InfoChip(label: 'Best', value: best)), const SizedBox(width: 8), Expanded(child: _InfoChip(label: 'Tough', value: tough))]),
                        const SizedBox(height: 8),
                        Row(children: [Expanded(child: _InfoChip(label: 'Entries', value: '$entries')), const SizedBox(width: 8), Expanded(child: _InfoChip(label: 'Coverage', value: coverage))]),
                        const SizedBox(height: 6),
                        Text('Tip: Multiple logs per day are fine — bar height is the daily average. Multi-colour shows all logs (weighted).', style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.65))),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMoodTab(BuildContext context) {
    if (_loadingMood) return const Center(child: CircularProgressIndicator());
    final monthList = _moodMonth;
    return AnimatedBackdrop(
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onHorizontalDragEnd: (details) {
          final vx = details.primaryVelocity ?? 0;
          if (vx < -100) setState(() => _monthCursor = DateTime(_monthCursor.year, _monthCursor.month + 1, 1));
          else if (vx > 100) setState(() => _monthCursor = DateTime(_monthCursor.year, _monthCursor.month - 1, 1));
        },
        child: ListView(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
          children: [
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(title: 'Mood History', subtitle: 'Swipe months to review your logs'),
                  _MonthHeader(
                    month: _monthCursor,
                    onPrev: () => setState(() => _monthCursor = DateTime(_monthCursor.year, _monthCursor.month - 1, 1)),
                    onNext: () => setState(() => _monthCursor = DateTime(_monthCursor.year, _monthCursor.month + 1, 1)),
                  ),
                  const SizedBox(height: 8),
                  _SummaryRow(avg: _avgMoodOf(monthList), count: monthList.length, bestStreak: _bestStreakOf(monthList)),
                  const SizedBox(height: 8),
                  if (monthList.isEmpty) const _EmptyState() else ..._buildMoodGroupWidgets(monthList),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TopTabChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _TopTabChip({required this.label, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) => ChoiceChip(label: Text(label), selected: selected, onSelected: (_) => onTap());
}

class _RangeChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const _RangeChip({required this.label, required this.selected, required this.onTap});
  @override
  Widget build(BuildContext context) => ChoiceChip(label: Text(label), selected: selected, onSelected: (_) => onTap());
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 24, 12, 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        boxShadow: const [BoxShadow(color: kCardShadow, blurRadius: 8, offset: Offset(0, 2))],
        border: Border.all(color: theme.dividerColor),
      ),
      child: Center(child: Text('Nothing here yet. Log a new mood to start tracking.', style: theme.textTheme.bodyMedium)),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final double avg;
  final int count;
  final int bestStreak;
  const _SummaryRow({required this.avg, required this.count, required this.bestStreak});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final avgText = avg == 0 ? '-' : avg.toStringAsFixed(1);
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.dividerColor),
        boxShadow: const [BoxShadow(color: kCardShadow, blurRadius: 8, offset: Offset(0, 2))],
      ),
      child: Row(
        children: [
          _chip(context, 'Avg', avgText),
          const SizedBox(width: 8),
          _chip(context, 'Entries', '$count'),
          const SizedBox(width: 8),
          _chip(context, 'Best streak', '$bestStreak'),
        ],
      ),
    );
  }
  Widget _chip(BuildContext context, String label, String value) {
    final theme = Theme.of(context);
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
        decoration: BoxDecoration(
          color: theme.colorScheme.primary.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: theme.dividerColor),
        ),
        child: Column(
          children: [
            Text(label, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.65))),
            const SizedBox(height: 4),
            Text(value, style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }
}

class _MoodCard extends StatelessWidget {
  final MoodEntry entry;
  const _MoodCard({required this.entry});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final day = DateFormat('EEE, MMM d • HH:mm').format(entry.timestamp);
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 6, 12, 6),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.dividerColor),
        boxShadow: const [BoxShadow(color: kCardShadow, blurRadius: 8, offset: Offset(0, 2))],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(entry.emoji, style: const TextStyle(fontSize: 22)),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('${entry.label} • $day', style: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w800)),
                if (entry.note.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(entry.note, style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.75))),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Text('${entry.mood}/5', style: theme.textTheme.bodyMedium?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.7), fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _MonthHeader extends StatelessWidget {
  final DateTime month;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  const _MonthHeader({required this.month, required this.onPrev, required this.onNext});
  @override
  Widget build(BuildContext context) {
    final title = DateFormat('MMMM yyyy').format(month);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4),
      child: Row(
        children: [
          IconButton(onPressed: onPrev, icon: const Icon(Icons.chevron_left)),
          Expanded(child: Text(title, textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16))),
          IconButton(onPressed: onNext, icon: const Icon(Icons.chevron_right)),
        ],
      ),
    );
  }
}

enum _BarLabelMode { week, month, year }

class _DailyMoodBars extends StatelessWidget {
  final List<_WeeklyPoint> points;
  final _BarLabelMode labelMode;
  final void Function(_WeeklyPoint p)? onBarTap;
  const _DailyMoodBars({required this.points, required this.labelMode, this.onBarTap});

  bool get _scrollable => labelMode != _BarLabelMode.week;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const chartH = 168.0;
    const barAreaH = 104.0;
    final itemWidth = (labelMode == _BarLabelMode.month) ? 56.0 : 64.0;
    final barsRow = SizedBox(
      height: barAreaH,
      child: _scrollable
          ? SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: points.map((p) => _barItem(context, p, barAreaH, width: itemWidth)).toList()),
            )
          : Row(crossAxisAlignment: CrossAxisAlignment.end, children: points.map((p) => Expanded(child: _barItem(context, p, barAreaH))).toList()),
    );
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor),
        boxShadow: const [BoxShadow(color: kCardShadow, blurRadius: 10, offset: Offset(0, 2))],
      ),
      child: SizedBox(
        height: chartH,
        child: Column(
          children: [
            barsRow,
            const SizedBox(height: 6),
            _labelsRow(context, itemWidth),
            const SizedBox(height: 6),
            _legendRow(context),
          ],
        ),
      ),
    );
  }

  Widget _labelsRow(BuildContext context, double itemWidth) {
    final theme = Theme.of(context);
    Widget labelFor(DateTime d) => Text(_labelFor(d, labelMode), maxLines: 1, overflow: TextOverflow.ellipsis, style: theme.textTheme.bodySmall?.copyWith(fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.70), fontWeight: FontWeight.w800));
    if (!_scrollable) return Row(children: points.map((p) => Expanded(child: Center(child: labelFor(p.day)))).toList());
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      physics: const BouncingScrollPhysics(),
      child: Row(children: points.map((p) => SizedBox(width: itemWidth, child: Center(child: labelFor(p.day)))).toList()),
    );
  }

  Widget _legendRow(BuildContext context) {
    final theme = Theme.of(context);
    Widget dot(Color c) => Container(width: 10, height: 10, decoration: BoxDecoration(color: c, shape: BoxShape.circle));
    TextStyle t() => theme.textTheme.bodySmall!.copyWith(fontSize: 11, fontWeight: FontWeight.w800, color: theme.colorScheme.onSurface.withValues(alpha: 0.70));
    const good = Color(0xFF2E7D32);
    const neutral = Color(0xFFF9A825);
    const bad = Color(0xFFC62828);
    return Wrap(
      alignment: WrapAlignment.center,
      spacing: 14,
      runSpacing: 6,
      children: [
        Row(mainAxisSize: MainAxisSize.min, children: [dot(good), const SizedBox(width: 6), Text('Good', style: t())]),
        Row(mainAxisSize: MainAxisSize.min, children: [dot(neutral), const SizedBox(width: 6), Text('Neutral', style: t())]),
        Row(mainAxisSize: MainAxisSize.min, children: [dot(bad), const SizedBox(width: 6), Text('Bad', style: t())]),
      ],
    );
  }

  static Color _moodColorForScore(double mood) {
    if (mood >= 4.0) return const Color(0xFF2E7D32);
    if (mood <= 2.0) return const Color(0xFFC62828);
    return const Color(0xFFF9A825);
  }

  Widget _barItem(BuildContext context, _WeeklyPoint p, double maxH, {double? width}) {
    final theme = Theme.of(context);
    final barValue = p.avg <= 0 ? 0.05 : (p.avg / 5.0);
    final barH = maxH * barValue;
    final barBody = ClipRRect(
      borderRadius: BorderRadius.circular(0),
      child: SizedBox(
        width: 14,
        height: barH,
        child: p.avg <= 0
            ? Container(color: theme.dividerColor)
            : (p.count <= 1 || p.entries.isEmpty)
                ? Container(color: p.entries.length == 1 ? _StackedSlices._segmentColor(p.entries.first.mood) : _moodColorForScore(p.avg))
                : _StackedSlices(entries: p.entries),
      ),
    );
    final frame = SizedBox(width: 14, height: maxH, child: Align(alignment: Alignment.bottomCenter, child: barBody));
    final withBadge = Stack(
      clipBehavior: Clip.none,
      children: [
        frame,
        if (p.count > 1)
          Positioned(
            top: -10,
            right: -8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
              decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(10), border: Border.all(color: theme.dividerColor), boxShadow: const [BoxShadow(color: kCardShadow, blurRadius: 8, offset: Offset(0, 2))]),
              child: Text('x${p.count}', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w900, fontSize: 11, color: theme.colorScheme.onSurface.withValues(alpha: 0.8))),
            ),
          ),
      ],
    );
    final tappable = (onBarTap != null) ? GestureDetector(behavior: HitTestBehavior.opaque, onTap: () => onBarTap!(p), child: withBadge) : withBadge;
    return SizedBox(width: width, child: Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Align(alignment: Alignment.bottomCenter, child: tappable)));
  }

  static String _labelFor(DateTime d, _BarLabelMode mode) {
    switch (mode) {
      case _BarLabelMode.week: return DateFormat('EEE').format(d).substring(0, 1);
      case _BarLabelMode.month: return DateFormat('MMM').format(d);
      case _BarLabelMode.year: return DateFormat('yyyy').format(d);
    }
  }
}

class _StackedSlices extends StatelessWidget {
  final List<MoodEntry> entries;
  const _StackedSlices({required this.entries});
  static Color _segmentColor(int mood) {
    if (mood >= 4) return const Color(0xFF2E7D32);
    if (mood <= 2) return const Color(0xFFC62828);
    return const Color(0xFFF9A825);
  }
  @override
  Widget build(BuildContext context) {
    if (entries.isEmpty) return const SizedBox.shrink();
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: entries.map((e) {
        final flex = e.mood.clamp(1, 10);
        return Expanded(flex: flex, child: Container(width: double.infinity, color: _segmentColor(e.mood)));
      }).toList(),
    );
  }
}

class _StatTile extends StatelessWidget {
  final String label;
  final String value;
  final IconData? icon;
  const _StatTile({required this.label, required this.value, this.icon});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: theme.colorScheme.surface, borderRadius: BorderRadius.circular(16), border: Border.all(color: theme.dividerColor)),
      child: Row(
        children: [
          if (icon != null) ...[Icon(icon, size: 18), const SizedBox(width: 6)],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface.withValues(alpha: 0.65))),
                const SizedBox(height: 2),
                Text(value, style: theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label;
  final String value;
  const _InfoChip({required this.label, required this.value});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.colorScheme.primary.withValues(alpha: 0.18)),
      ),
      child: Text('$label: $value', style: theme.textTheme.bodySmall?.copyWith(fontWeight: FontWeight.w800), overflow: TextOverflow.ellipsis),
    );
  }
}
