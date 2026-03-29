// lib/pages/daily_hub_screen.dart
import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

// Relative imports
import '../widgets/page_scaffold.dart';

import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/services/daily_insight_engine_service.dart';
import 'package:mindcore_ai/services/knowledge_snapshot_service.dart';
import 'package:mindcore_ai/services/smart_nudge_engine.dart';
import 'package:mindcore_ai/services/premium_service.dart';

import 'package:mindcore_ai/pages/helpers/journal_service.dart';

import 'package:shared_preferences/shared_preferences.dart';

// ✅ NEW: Journal reflections
import 'package:mindcore_ai/services/journal_reflection_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';
import 'package:mindcore_ai/widgets/tts_speaker_button.dart';

// PDF export + share
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

class DailyHubScreen extends StatefulWidget {
  const DailyHubScreen({super.key});

  @override
  State<DailyHubScreen> createState() => _DailyHubScreenState();
}

class _DailyHubScreenState extends State<DailyHubScreen>
    with AutoStopTtsRouteAware<DailyHubScreen> {
  final TextEditingController _journalCtrl = TextEditingController();
  bool _saving = false;
  bool _exporting = false;
  bool _syncing = false;

  List<JournalEntry> _entries = const <JournalEntry>[];
  DailyInsightBundle _dailyInsight = DailyInsightBundle.fallback;
  KnowledgeSnapshot? _knowledgeSnapshot;
  bool _insightLoading = true;

  /// Calendar month cursor
  DateTime _monthCursor = DateTime(DateTime.now().year, DateTime.now().month);

  /// Month animation direction: -1 = back, +1 = forward
  int _monthDir = 1;

  /// Draft autosave debounce
  Timer? _draftTimer;

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
    _loadEntries();
    _loadDraftForToday();
    unawaited(_loadInsightBundle());
    unawaited(SmartNudgeEngine.scheduleGentleDailyNudge());
    _journalCtrl.addListener(_scheduleDraftSave);
  }

  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      if (mounted) Navigator.of(context).pop();
    }
  }

  Future<void> _loadInsightBundle({bool forceRefresh = false}) async {
    final snapshot = await KnowledgeSnapshotService.buildSnapshot();
    final moodHint = snapshot.dominantState == 'low'
        ? 'low'
        : snapshot.dominantState == 'fragile'
            ? 'anxious'
            : snapshot.dominantState == 'uplifted'
                ? 'motivated'
                : 'calm';

    final bundle = await DailyInsightEngineService.getBundle(
      moodLabel: moodHint,
      contextSummary: snapshot.summary,
      forceRefresh: forceRefresh,
    );

    if (!mounted) return;
    setState(() {
      _knowledgeSnapshot = snapshot;
      _dailyInsight = bundle;
      _insightLoading = false;
    });
  }

  Future<void> _refreshMindCoreLayer() async {
    await DailyInsightEngineService.invalidateToday();
    await _loadInsightBundle(forceRefresh: true);
    unawaited(SmartNudgeEngine.scheduleGentleDailyNudge());
  }

  @override
  void dispose() {
    _draftTimer?.cancel();
    _journalCtrl.removeListener(_scheduleDraftSave);
    _journalCtrl.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  // --------------------------
  // Draft autosave (Today only)
  // --------------------------

  String get _draftKey {
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    return 'journal_draft_$today';
  }

  Future<void> _loadDraftForToday() async {
    try {
      final raw = await _DraftStore.getString(_draftKey);
      if (!mounted) return;
      if (raw != null &&
          raw.trim().isNotEmpty &&
          _journalCtrl.text.trim().isEmpty) {
        setState(() {
          _journalCtrl.text = raw;
          _journalCtrl.selection =
              TextSelection.collapsed(offset: _journalCtrl.text.length);
        });
      }
    } catch (_) {}
  }

  void _scheduleDraftSave() {
    if (_saving) return;

    _draftTimer?.cancel();
    _draftTimer = Timer(const Duration(milliseconds: 450), () async {
      final text = _journalCtrl.text;
      if (text.trim().isEmpty) {
        await _DraftStore.remove(_draftKey);
      } else {
        await _DraftStore.setString(_draftKey, text);
      }
    });
  }

  Future<void> _clearDraftForToday() async {
    await _DraftStore.remove(_draftKey);
  }

  // --------------------------
  // Entries
  // --------------------------

  Future<void> _loadEntries() async {
    try {
      final ent = await JournalService.getEntries();
      if (!mounted) return;
      setState(() => _entries = ent);
      unawaited(_loadInsightBundle());
    } catch (_) {
      if (!mounted) return;
      setState(() => _entries = const <JournalEntry>[]);
    }
  }

  Future<void> _syncNow() async {
    if (_saving || _exporting || _syncing) return;

    setState(() => _syncing = true);
    HapticFeedback.lightImpact();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Syncing journal from cloud…')),
    );

    try {
      await JournalService.syncFromFirestore();
      await _loadEntries();
      await _refreshMindCoreLayer();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('✅ Journal synced from cloud')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('⚠️ Sync failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  Future<void> _saveJournal() async {
    final note = _journalCtrl.text.trim();
    if (note.isEmpty || _saving) return;

    HapticFeedback.lightImpact();

    setState(() => _saving = true);
    try {
      final res = await JournalService.addEntry(note);
      final cloudOk = res.cloudOk;

      _journalCtrl.clear();
      await _clearDraftForToday();

      final fresh = await JournalService.getEntries();
      if (mounted) setState(() => _entries = fresh);
      await _refreshMindCoreLayer();

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              cloudOk ? '✅ Journal saved to cloud' : '⚠️ Saved locally only'),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not save: $e')),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  // --------------------------
  // ✅ NEW: Reflection UI
  // --------------------------

  Future<void> _speakJournalText(String text,
      {TtsSurface surface = TtsSurface.journal}) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    await OpenAiTtsService.instance.speak(
      trimmed,
      moodLabel: 'calm',
      surface: surface,
      messageId: '${surface.name}_${trimmed.hashCode}',
      force: true,
    );
  }

  Future<void> _showReflection(JournalEntry entry) async {
    HapticFeedback.lightImpact();

    // Requires JournalEntry.id
    final cached = await JournalReflectionService.instance.getCached(entry.id);

    if (!mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        final t = Theme.of(ctx).textTheme;

        Future<void> run({bool refresh = false}) async {
          final text = await JournalReflectionService.instance.reflect(
            entryId: entry.id,
            note: entry.note,
            moodLabel: 'Neutral',
            forceRefresh: refresh,
          );
          if (!ctx.mounted) return;
          Navigator.pop(ctx);
          await _showReflectionResult(entry, text);
        }

        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.auto_awesome_rounded, color: scheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'AI Reflection',
                        style: t.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w900),
                      ),
                    ),
                    if (cached != null && cached.trim().isNotEmpty)
                      TtsSpeakerButton(
                        text: cached,
                        surface: TtsSurface.reflection,
                        moodLabel: 'calm',
                        messageId: 'reflection_cached_${entry.id}',
                      ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Get a short, supportive reflection + micro-step.',
                  style: t.bodySmall?.copyWith(
                    color: t.bodySmall?.color?.withValues(alpha: 0.75),
                  ),
                ),
                const SizedBox(height: 12),
                if (cached != null && cached.trim().isNotEmpty)
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: scheme.surface,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: scheme.outlineVariant.withValues(alpha: 0.35)),
                    ),
                    child: Text(
                      cached,
                      style: t.bodyMedium?.copyWith(height: 1.35),
                    ),
                  ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonal(
                        onPressed: () => run(refresh: false),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Generate'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => run(refresh: true),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Refresh'),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _showReflectionResult(JournalEntry entry, String text) async {
    if (!mounted) return;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        final t = Theme.of(ctx).textTheme;

        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.psychology_alt_rounded, color: scheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Reflection',
                        style: t.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w900),
                      ),
                    ),
                    TtsSpeakerButton(
                      text: text,
                      surface: TtsSurface.reflection,
                      moodLabel: 'calm',
                      messageId: 'reflection_result_${entry.id}',
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: scheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: scheme.outlineVariant.withValues(alpha: 0.35)),
                  ),
                  child: Text(
                    text,
                    style: t.bodyMedium?.copyWith(height: 1.35),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonal(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 12),
                      child: Text('Close'),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  // --------------------------
  // Edit / Add for specific day
  // --------------------------

  Future<bool> _confirmOverwrite(BuildContext ctx) async {
    final t = Theme.of(ctx).textTheme;
    return (await showDialog<bool>(
          context: ctx,
          builder: (dctx) => AlertDialog(
            title: Text('Save changes?',
                style: t.titleMedium?.copyWith(fontWeight: FontWeight.w900)),
            content: const Text(
                'This will overwrite the existing text for this page.'),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(dctx, false),
                  child: const Text('Cancel')),
              FilledButton(
                  onPressed: () => Navigator.pop(dctx, true),
                  child: const Text('Save')),
            ],
          ),
        )) ??
        false;
  }

  Future<void> _editEntry(JournalEntry entry) async {
    HapticFeedback.lightImpact();

    final original = entry.note.trim();
    final ctrl = TextEditingController(text: entry.note);

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        final t = Theme.of(ctx).textTheme;

        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.edit_rounded, color: scheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('Edit Page',
                          style: t.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w900)),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  DateFormat('EEEE, d MMMM • HH:mm').format(entry.timestamp),
                  style: t.bodySmall?.copyWith(
                      color: t.bodySmall?.color?.withValues(alpha: 0.75)),
                ),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(
                    color: scheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: scheme.outlineVariant.withValues(alpha: 0.45)),
                  ),
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                  child: TextField(
                    controller: ctrl,
                    minLines: 7,
                    maxLines: 14,
                    textInputAction: TextInputAction.newline,
                    decoration: const InputDecoration(
                        border: InputBorder.none, hintText: 'Edit your entry…'),
                    style: t.bodyLarge?.copyWith(height: 1.35),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonal(
                        onPressed: () => Navigator.pop(ctx, false),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Cancel'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () async {
                          final updated = ctrl.text.trim();
                          if (updated.isEmpty) return;

                          if (updated != original) {
                            final ok = await _confirmOverwrite(ctx);
                            if (!ok) return;
                          }

                          final ok = await JournalService.updateEntry(
                              entry.timestamp, updated);
                          Navigator.pop(ctx, ok);
                        },
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Save Changes'),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );

    ctrl.dispose();

    if (saved == true) {
      await _loadEntries();
      await _refreshMindCoreLayer();
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Entry updated')));
    }
  }

  Future<void> _addEntryForDay(DateTime day) async {
    HapticFeedback.lightImpact();

    final ctrl = TextEditingController();

    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final scheme = Theme.of(ctx).colorScheme;
        final t = Theme.of(ctx).textTheme;

        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.note_add_rounded, color: scheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text('New Page',
                          style: t.titleMedium
                              ?.copyWith(fontWeight: FontWeight.w900)),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx, false),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  DateFormat('EEEE, d MMMM').format(day),
                  style: t.bodySmall?.copyWith(
                      color: t.bodySmall?.color?.withValues(alpha: 0.75)),
                ),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(
                    color: scheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                        color: scheme.outlineVariant.withValues(alpha: 0.45)),
                  ),
                  padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
                  child: TextField(
                    controller: ctrl,
                    minLines: 7,
                    maxLines: 14,
                    textInputAction: TextInputAction.newline,
                    decoration: const InputDecoration(
                        border: InputBorder.none,
                        hintText: 'Write your entry…'),
                    style: t.bodyLarge?.copyWith(height: 1.35),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonal(
                        onPressed: () => Navigator.pop(ctx, false),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Cancel'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: () async {
                          final note = ctrl.text.trim();
                          if (note.isEmpty) return;

                          final now = DateTime.now();
                          final when = DateTime(day.year, day.month, day.day,
                              now.hour, now.minute, now.second);

                          final res =
                              await JournalService.addEntry(note, when: when);
                          Navigator.pop(ctx, res.cloudOk);
                        },
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Save'),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );

    ctrl.dispose();

    if (saved != null) {
      await _loadEntries();
      await _refreshMindCoreLayer();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: Text(
                saved ? '✅ Journal saved to cloud' : '⚠️ Saved locally only')),
      );
    }
  }

  // --------------------------
  // Grouping + streak
  // --------------------------

  Map<String, List<JournalEntry>> _groupByDay(List<JournalEntry> entries) {
    final map = <String, List<JournalEntry>>{};
    for (final e in entries) {
      final dayKey = DateFormat('yyyy-MM-dd').format(
        DateTime(e.timestamp.year, e.timestamp.month, e.timestamp.day),
      );
      (map[dayKey] ??= []).add(e);
    }
    for (final k in map.keys) {
      map[k]!.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    }
    return map;
  }

  int _currentStreak(Map<String, List<JournalEntry>> grouped) {
    final today = DateTime.now();
    int streak = 0;

    for (int i = 0; i < 5000; i++) {
      final d = DateTime(today.year, today.month, today.day)
          .subtract(Duration(days: i));
      final key = DateFormat('yyyy-MM-dd').format(d);
      if ((grouped[key] ?? const []).isEmpty) break;
      streak++;
    }
    return streak;
  }

  _MonthSummary _monthSummary(
      DateTime month, Map<String, List<JournalEntry>> grouped) {
    final monthStart = DateTime(month.year, month.month, 1);
    final monthEnd = DateTime(month.year, month.month + 1, 1)
        .subtract(const Duration(days: 1));

    int daysWithEntries = 0;
    int totalEntries = 0;

    for (DateTime d = monthStart;
        !d.isAfter(monthEnd);
        d = d.add(const Duration(days: 1))) {
      final key = DateFormat('yyyy-MM-dd').format(d);
      final list = grouped[key] ?? const <JournalEntry>[];
      if (list.isNotEmpty) daysWithEntries++;
      totalEntries += list.length;
    }

    return _MonthSummary(
      daysWithEntries: daysWithEntries,
      totalEntries: totalEntries,
      streak: _currentStreak(grouped),
    );
  }

  // --------------------------
  // Export month (PDF — premium diary)
  // --------------------------
  // (kept exactly as you provided)
  Future<void> _exportMonthAsPdf(
      DateTime month, Map<String, List<JournalEntry>> grouped) async {
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      return;
    }
    if (_exporting) return;
    setState(() => _exporting = true);

    try {
      HapticFeedback.lightImpact();

      final monthLabel = DateFormat('MMMM yyyy').format(month);
      final summary = _monthSummary(month, grouped);

      final monthStart = DateTime(month.year, month.month, 1);
      final monthEnd = DateTime(month.year, month.month + 1, 1)
          .subtract(const Duration(days: 1));

      final pdf = pw.Document();

      pdf.addPage(
        pw.Page(
          pageTheme: pw.PageTheme(
            margin: const pw.EdgeInsets.all(36),
            theme: pw.ThemeData.withFont(
              base: pw.Font.helvetica(),
              bold: pw.Font.helveticaBold(),
            ),
          ),
          build: (ctx) {
            return pw.Container(
              decoration: pw.BoxDecoration(
                border: pw.Border.all(color: PdfColors.grey300, width: 1),
                borderRadius: pw.BorderRadius.circular(14),
              ),
              padding: const pw.EdgeInsets.all(24),
              child: pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Text(
                    'MindReset AI',
                    style: pw.TextStyle(
                      fontSize: 18,
                      fontWeight: pw.FontWeight.bold,
                      color: PdfColors.blueGrey800,
                    ),
                  ),
                  pw.SizedBox(height: 6),
                  pw.Text(
                    'Journal Book',
                    style: pw.TextStyle(
                      fontSize: 28,
                      fontWeight: pw.FontWeight.bold,
                    ),
                  ),
                  pw.SizedBox(height: 8),
                  pw.Text(
                    monthLabel,
                    style: pw.TextStyle(fontSize: 14, color: PdfColors.grey700),
                  ),
                  pw.SizedBox(height: 16),
                  pw.Divider(color: PdfColors.grey300),
                  pw.SizedBox(height: 14),
                  pw.Text(
                    'Monthly Reflection Snapshot',
                    style: pw.TextStyle(
                        fontSize: 13,
                        fontWeight: pw.FontWeight.bold,
                        color: PdfColors.blueGrey800),
                  ),
                  pw.SizedBox(height: 10),
                  pw.Row(
                    mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                    children: [
                      _pdfStat('Days written', '${summary.daysWithEntries}',
                          PdfColors.blueGrey800),
                      _pdfStat('Entries', '${summary.totalEntries}',
                          PdfColors.blueGrey800),
                      _pdfStat('Current streak', '${summary.streak} days',
                          PdfColors.blueGrey800),
                    ],
                  ),
                  pw.SizedBox(height: 18),
                  pw.Container(
                    padding: const pw.EdgeInsets.all(12),
                    decoration: pw.BoxDecoration(
                      color: PdfColors.grey100,
                      borderRadius: pw.BorderRadius.circular(10),
                      border: pw.Border.all(color: PdfColors.grey300),
                    ),
                    child: pw.Text(
                      'Created privately on your device.\n'
                      'Share only if you choose — your wellbeing comes first.',
                      style: pw.TextStyle(
                          fontSize: 10.5, color: PdfColors.grey800),
                    ),
                  ),
                  pw.Spacer(),
                  pw.Align(
                    alignment: pw.Alignment.bottomRight,
                    child: pw.Text(
                      'Generated on ${DateFormat('d MMM yyyy').format(DateTime.now())}',
                      style:
                          pw.TextStyle(fontSize: 10, color: PdfColors.grey600),
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      );

      pdf.addPage(
        pw.MultiPage(
          pageTheme: pw.PageTheme(
            margin: const pw.EdgeInsets.all(32),
            theme: pw.ThemeData.withFont(
              base: pw.Font.helvetica(),
              bold: pw.Font.helveticaBold(),
            ),
          ),
          footer: (ctx) => pw.Container(
            alignment: pw.Alignment.centerRight,
            margin: const pw.EdgeInsets.only(top: 14),
            child: pw.Text(
              'Page ${ctx.pageNumber} of ${ctx.pagesCount}',
              style: pw.TextStyle(fontSize: 10, color: PdfColors.grey600),
            ),
          ),
          build: (ctx) {
            final widgets = <pw.Widget>[];

            for (DateTime d = monthStart;
                !d.isAfter(monthEnd);
                d = d.add(const Duration(days: 1))) {
              final key = DateFormat('yyyy-MM-dd').format(d);
              final dayEntries = grouped[key] ?? const <JournalEntry>[];
              if (dayEntries.isEmpty) continue;

              widgets.add(
                pw.Padding(
                  padding: const pw.EdgeInsets.only(top: 14, bottom: 6),
                  child: pw.Text(
                    DateFormat('EEEE, d MMMM').format(d),
                    style: pw.TextStyle(
                        fontSize: 14, fontWeight: pw.FontWeight.bold),
                  ),
                ),
              );

              for (final e in dayEntries.reversed) {
                widgets.add(
                  pw.Container(
                    margin: const pw.EdgeInsets.only(left: 6, bottom: 10),
                    padding: const pw.EdgeInsets.only(left: 10),
                    decoration: pw.BoxDecoration(
                      border: pw.Border(
                        left: pw.BorderSide(
                            width: 2, color: PdfColors.blueGrey200),
                      ),
                    ),
                    child: pw.Column(
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Text(
                          DateFormat('HH:mm').format(e.timestamp),
                          style: pw.TextStyle(
                              fontSize: 9, color: PdfColors.grey700),
                        ),
                        pw.SizedBox(height: 3),
                        pw.Text(
                          e.note.trim(),
                          style: const pw.TextStyle(fontSize: 11),
                        ),
                      ],
                    ),
                  ),
                );
              }

              widgets.add(pw.SizedBox(height: 4));
            }

            if (widgets.isEmpty) {
              return [
                pw.Text('No journal entries for this month.',
                    style: const pw.TextStyle(fontSize: 12)),
              ];
            }

            widgets.add(
              pw.Padding(
                padding: const pw.EdgeInsets.only(top: 10),
                child: pw.Text(
                  'Created with MindReset AI • Private by design',
                  style: pw.TextStyle(fontSize: 9.5, color: PdfColors.grey600),
                ),
              ),
            );

            return widgets;
          },
        ),
      );

      final dir = await getApplicationDocumentsDirectory();
      final safeMonth = DateFormat('yyyy_MM').format(month);
      final fileName = 'MindReset_Journal_$safeMonth.pdf';
      final file = File('${dir.path}/$fileName');

      await file.writeAsBytes(await pdf.save());

      if (!mounted) return;

      await SharePlus.instance.share(ShareParams(
          files: [XFile(file.path)],
          subject: 'My MindReset Journal — $monthLabel'));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not export PDF: $e')),
      );
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  static pw.Widget _pdfStat(String label, String value, PdfColor color) {
    return pw.Container(
      width: 150,
      padding: const pw.EdgeInsets.all(10),
      decoration: pw.BoxDecoration(
        border: pw.Border.all(color: PdfColors.grey300),
        borderRadius: pw.BorderRadius.circular(10),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(label,
              style: pw.TextStyle(fontSize: 9.5, color: PdfColors.grey700)),
          pw.SizedBox(height: 4),
          pw.Text(value,
              style: pw.TextStyle(
                  fontSize: 12.5,
                  fontWeight: pw.FontWeight.bold,
                  color: color)),
        ],
      ),
    );
  }

  // --------------------------
  // Day view + delete/undo
  // --------------------------

  Future<void> _deleteEntryWithUndo(JournalEntry entry) async {
    HapticFeedback.lightImpact();

    final removed = await JournalService.deleteEntry(entry.timestamp);
    if (removed == null) return;

    await _loadEntries();
    await _refreshMindCoreLayer();
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Entry deleted'),
        action: SnackBarAction(
          label: 'Undo',
          onPressed: () async {
            final res = await JournalService.addEntry(removed.note,
                when: removed.timestamp);
            await _loadEntries();
            if (!mounted) return;
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                  content: Text(res.cloudOk
                      ? '✅ Restored to cloud'
                      : '⚠️ Restored locally only')),
            );
          },
        ),
      ),
    );
  }

  Future<void> _openDayEntries(
      DateTime day, List<JournalEntry> dayEntries) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) {
        final t = Theme.of(ctx).textTheme;
        final scheme = Theme.of(ctx).colorScheme;

        return Padding(
          padding: EdgeInsets.only(
            left: 16,
            right: 16,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 16,
          ),
          child: GlassCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.event_note_rounded, color: scheme.primary),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        DateFormat('EEEE, d MMMM').format(day),
                        style: t.titleMedium
                            ?.copyWith(fontWeight: FontWeight.w900),
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.pop(ctx),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonal(
                    onPressed: () {
                      Navigator.pop(ctx);
                      _addEntryForDay(day);
                    },
                    child: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 10),
                      child: Text('Add another entry for this day'),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                ...dayEntries.map((e) {
                  final time = DateFormat('HH:mm').format(e.timestamp);
                  final preview = e.note.trim().length > 120
                      ? '${e.note.trim().substring(0, 120)}…'
                      : e.note.trim();

                  return Container(
                    margin: const EdgeInsets.only(top: 10),
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: scheme.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(
                          color: scheme.outlineVariant.withValues(alpha: 0.35)),
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () async {
                              Navigator.pop(ctx);
                              await _editEntry(e);
                            },
                            borderRadius: BorderRadius.circular(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(time,
                                        style: t.labelMedium?.copyWith(
                                            fontWeight: FontWeight.w800)),
                                    const Spacer(),
                                    Icon(Icons.edit_rounded,
                                        size: 18,
                                        color: scheme.primary
                                            .withValues(alpha: 0.85)),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(preview,
                                    style:
                                        t.bodyMedium?.copyWith(height: 1.35)),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),

                        // ✅ NEW: Reflect + Delete actions
                        Column(
                          children: [
                            TtsSpeakerButton(
                              text: e.note,
                              surface: TtsSurface.journal,
                              moodLabel: 'calm',
                              messageId: 'journal_entry_${e.id}',
                              iconColor: scheme.primary.withValues(alpha: 0.90),
                            ),
                            IconButton(
                              tooltip: 'Reflect',
                              onPressed: () {
                                Navigator.pop(ctx);
                                _showReflection(e);
                              },
                              icon: Icon(Icons.auto_awesome_rounded,
                                  color:
                                      scheme.primary.withValues(alpha: 0.90)),
                            ),
                            IconButton(
                              tooltip: 'Delete',
                              onPressed: () {
                                Navigator.pop(ctx);
                                _deleteEntryWithUndo(e);
                              },
                              icon: Icon(Icons.delete_outline_rounded,
                                  color: scheme.error.withValues(alpha: 0.85)),
                            ),
                          ],
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ],
            ),
          ),
        );
      },
    );
  }

  // --------------------------
  // Month navigation
  // --------------------------

  void _prevMonth() {
    HapticFeedback.lightImpact();
    setState(() {
      _monthDir = -1;
      _monthCursor = DateTime(_monthCursor.year, _monthCursor.month - 1);
    });
  }

  void _nextMonth() {
    HapticFeedback.lightImpact();
    setState(() {
      _monthDir = 1;
      _monthCursor = DateTime(_monthCursor.year, _monthCursor.month + 1);
    });
  }

  // --------------------------
  // UI
  // --------------------------

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final todayText = DateFormat('EEEE, d MMMM').format(now);
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;

    final grouped = _groupByDay(_entries);
    final streak = _currentStreak(grouped);
    final monthKey = ValueKey('${_monthCursor.year}-${_monthCursor.month}');

    return PageScaffold(
      title: 'Journal',
      bottomIndex: 2,
      body: AnimatedBackdrop(
        child: RefreshIndicator(
          onRefresh: _loadEntries,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            children: [
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            todayText,
                            style: t.titleMedium?.copyWith(
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.2,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'A private page for your thoughts.',
                            style: t.bodySmall?.copyWith(
                              color:
                                  t.bodySmall?.color?.withValues(alpha: 0.75),
                            ),
                          ),
                        ],
                      ),
                    ),

                    // ✅ Sync button
                    IconButton(
                      tooltip: _syncing ? 'Syncing…' : 'Sync now',
                      onPressed: _syncing ? null : _syncNow,
                      icon: _syncing
                          ? SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.2,
                                color: scheme.primary,
                              ),
                            )
                          : Icon(
                              Icons.sync_rounded,
                              color: scheme.primary.withValues(alpha: 0.9),
                            ),
                    ),

                    if (streak > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: scheme.primary.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                          border: Border.all(
                              color: scheme.primary.withValues(alpha: 0.22)),
                        ),
                        child: Text(
                          '🔥 $streak day streak',
                          style: t.labelMedium?.copyWith(
                            fontWeight: FontWeight.w900,
                            color: scheme.primary,
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              _buildMindCoreInsightCard(context),
              const SizedBox(height: 12),

              // Composer
              GlassCard(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _sectionTitle(
                        context, 'Today’s Entry', Icons.menu_book_rounded),
                    const SizedBox(height: 12),
                    Container(
                      decoration: BoxDecoration(
                        color: scheme.surface,
                        borderRadius: BorderRadius.circular(16),
                        border: Border.all(
                            color:
                                scheme.outlineVariant.withValues(alpha: 0.45)),
                        boxShadow: const [
                          BoxShadow(
                            blurRadius: 10,
                            color: Color(0x12000000),
                            offset: Offset(0, 3),
                          ),
                        ],
                      ),
                      child: Stack(
                        children: [
                          Positioned.fill(
                            left: 0,
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: Container(
                                width: 10,
                                decoration: BoxDecoration(
                                  color: scheme.primary.withValues(alpha: 0.10),
                                  borderRadius: const BorderRadius.horizontal(
                                      left: Radius.circular(16)),
                                ),
                              ),
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
                            child: TextField(
                              controller: _journalCtrl,
                              minLines: 7,
                              maxLines: 12,
                              textInputAction: TextInputAction.newline,
                              decoration: InputDecoration(
                                hintText:
                                    'Write freely…\n\nWhat’s on your mind today?\nWhat do you want to let go of?',
                                border: InputBorder.none,
                                hintStyle: t.bodyMedium?.copyWith(
                                  height: 1.35,
                                  color: t.bodyMedium?.color
                                      ?.withValues(alpha: 0.55),
                                ),
                              ),
                              style: t.bodyLarge?.copyWith(height: 1.35),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton(
                            onPressed: _saving ? null : _saveJournal,
                            child: Padding(
                              padding:
                                  const EdgeInsets.symmetric(vertical: 12.0),
                              child: Text(_saving ? 'Saving…' : 'Save Entry'),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        TtsSpeakerButton(
                          text: _journalCtrl.text,
                          surface: TtsSurface.journal,
                          moodLabel: 'calm',
                          messageId: 'journal_draft_live',
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Autosaved draft • Saved locally • Pull down to refresh',
                      style: t.bodySmall?.copyWith(
                        color: t.bodySmall?.color?.withValues(alpha: 0.7),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 12),

              // Calendar “Recent Pages” with direction-aware animation + export
              GlassCard(
                padding: const EdgeInsets.all(18),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 240),
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeIn,
                  transitionBuilder: (child, anim) {
                    final begin = Offset(_monthDir * 0.10, 0);
                    final offsetTween =
                        Tween<Offset>(begin: begin, end: Offset.zero)
                            .chain(CurveTween(curve: Curves.easeOut));
                    return FadeTransition(
                      opacity: anim,
                      child: SlideTransition(
                          position: anim.drive(offsetTween), child: child),
                    );
                  },
                  child: _JournalCalendar(
                    key: monthKey,
                    month: _monthCursor,
                    groupedByDay: grouped,
                    onPrevMonth: _prevMonth,
                    onNextMonth: _nextMonth,
                    onExportMonth: _exporting
                        ? null
                        : () => _exportMonthAsPdf(_monthCursor, grouped),
                    onDayTap: (day) {
                      HapticFeedback.lightImpact();
                      final key = DateFormat('yyyy-MM-dd').format(day);
                      final list = grouped[key] ?? const <JournalEntry>[];
                      if (list.isEmpty) return;
                      _openDayEntries(day, list);
                    },
                    onDayLongPress: (day) => _addEntryForDay(day),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMindCoreInsightCard(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;
    final snapshot = _knowledgeSnapshot;

    return GlassCard(
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome_rounded, color: scheme.primary),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Today’s MindCore Insight',
                  style: t.titleMedium?.copyWith(fontWeight: FontWeight.w900),
                ),
              ),
              if (!_insightLoading)
                TtsSpeakerButton(
                  text:
                      '${_dailyInsight.summaryLine} ${_dailyInsight.affirmation} ${_dailyInsight.tip} ${_dailyInsight.reflectionPrompt}',
                  surface: TtsSurface.recommendation,
                  moodLabel: 'calm',
                  messageId: 'daily_insight_bundle',
                ),
            ],
          ),
          const SizedBox(height: 10),
          if (_insightLoading)
            const LinearProgressIndicator(minHeight: 3)
          else ...[
            if (snapshot != null)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _InsightPill(label: 'State: ${snapshot.dominantState}'),
                  _InsightPill(label: 'Focus: ${snapshot.recommendedFocus}'),
                  _InsightPill(
                      label:
                          'Mood avg: ${snapshot.recentMoodAverage.toStringAsFixed(1)}/5'),
                ],
              ),
            const SizedBox(height: 12),
            _InsightBlock(
              title: 'Summary',
              body: _dailyInsight.summaryLine,
              icon: Icons.lightbulb_outline_rounded,
            ),
            const SizedBox(height: 10),
            _InsightBlock(
              title: 'Affirmation',
              body: _dailyInsight.affirmation,
              icon: Icons.favorite_border_rounded,
            ),
            const SizedBox(height: 10),
            _InsightBlock(
              title: 'Micro-step',
              body: _dailyInsight.tip,
              icon: Icons.check_circle_outline_rounded,
            ),
            const SizedBox(height: 10),
            _InsightBlock(
              title: 'Reflection prompt',
              body: _dailyInsight.reflectionPrompt,
              icon: Icons.edit_note_rounded,
            ),
          ],
        ],
      ),
    );
  }

  Widget _sectionTitle(BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(fontWeight: FontWeight.w900),
        ),
      ],
    );
  }
}

class _InsightPill extends StatelessWidget {
  final String label;
  const _InsightPill({required this.label});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: scheme.primary.withValues(alpha: 0.14)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              fontWeight: FontWeight.w700,
              color: scheme.primary,
            ),
      ),
    );
  }
}

class _InsightBlock extends StatelessWidget {
  final String title;
  final String body;
  final IconData icon;
  const _InsightBlock({
    required this.title,
    required this.body,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(16),
        border:
            Border.all(color: scheme.outlineVariant.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: scheme.primary),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: t.labelLarge?.copyWith(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(body, style: t.bodyMedium?.copyWith(height: 1.35)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _JournalCalendar extends StatelessWidget {
  final DateTime month; // first day-of-month cursor
  final Map<String, List<JournalEntry>> groupedByDay;

  final VoidCallback onPrevMonth;
  final VoidCallback onNextMonth;

  /// null = disabled
  final VoidCallback? onExportMonth;

  final ValueChanged<DateTime> onDayTap;
  final ValueChanged<DateTime> onDayLongPress;

  const _JournalCalendar({
    super.key,
    required this.month,
    required this.groupedByDay,
    required this.onPrevMonth,
    required this.onNextMonth,
    required this.onExportMonth,
    required this.onDayTap,
    required this.onDayLongPress,
  });

  DateTime _firstDayOfMonth(DateTime d) => DateTime(d.year, d.month, 1);

  int _daysInMonth(DateTime d) {
    final nextMonth = DateTime(d.year, d.month + 1, 1);
    return nextMonth.subtract(const Duration(days: 1)).day;
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;

    final first = _firstDayOfMonth(month);
    final days = _daysInMonth(month);

    final firstWeekday = first.weekday; // 1..7
    final leadingEmpty = firstWeekday - 1;

    final totalCells = leadingEmpty + days;
    final trailingEmpty = (7 - (totalCells % 7)) % 7;
    final cellCount = totalCells + trailingEmpty;

    final monthLabel = DateFormat('MMMM yyyy').format(month);

    const weekLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.calendar_month_rounded, color: scheme.primary),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Recent Pages',
                style: t.titleMedium?.copyWith(fontWeight: FontWeight.w900),
              ),
            ),
            IconButton(
              tooltip:
                  onExportMonth == null ? 'Exporting…' : 'Export month as PDF',
              onPressed: onExportMonth,
              icon: Icon(
                onExportMonth == null
                    ? Icons.hourglass_top_rounded
                    : Icons.picture_as_pdf_rounded,
                color: scheme.primary.withValues(alpha: 0.9),
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            IconButton(
                onPressed: onPrevMonth,
                icon: const Icon(Icons.chevron_left_rounded)),
            Expanded(
              child: Center(
                child: Text(
                  monthLabel,
                  style: t.titleSmall?.copyWith(fontWeight: FontWeight.w800),
                ),
              ),
            ),
            IconButton(
                onPressed: onNextMonth,
                icon: const Icon(Icons.chevron_right_rounded)),
          ],
        ),
        const SizedBox(height: 6),
        Row(
          children: weekLabels
              .map(
                (w) => Expanded(
                  child: Center(
                    child: Text(
                      w,
                      style: t.labelSmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: t.labelSmall?.color?.withValues(alpha: 0.7),
                      ),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 8),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: cellCount,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 7,
            mainAxisSpacing: 8,
            crossAxisSpacing: 8,
            childAspectRatio: 1,
          ),
          itemBuilder: (ctx, i) {
            final dayNum = i - leadingEmpty + 1;
            if (dayNum < 1 || dayNum > days) return const SizedBox.shrink();

            final day = DateTime(month.year, month.month, dayNum);
            final key = DateFormat('yyyy-MM-dd').format(day);

            final entries = groupedByDay[key] ?? const <JournalEntry>[];
            final hasEntry = entries.isNotEmpty;

            final now = DateTime.now();
            final isToday = now.year == day.year &&
                now.month == day.month &&
                now.day == day.day;

            return _DayCell(
              day: dayNum,
              isToday: isToday,
              hasEntry: hasEntry,
              count: entries.length,
              onTap: hasEntry ? () => onDayTap(day) : null,
              onLongPress: () => onDayLongPress(day),
            );
          },
        ),
        const SizedBox(height: 10),
        Text(
          'Tap a highlighted day to view & edit • Long-press any day to add a page.',
          style: t.bodySmall
              ?.copyWith(color: t.bodySmall?.color?.withValues(alpha: 0.75)),
        ),
      ],
    );
  }
}

class _DayCell extends StatefulWidget {
  final int day;
  final bool isToday;
  final bool hasEntry;
  final int count;
  final VoidCallback? onTap;
  final VoidCallback onLongPress;

  const _DayCell({
    required this.day,
    required this.isToday,
    required this.hasEntry,
    required this.count,
    required this.onTap,
    required this.onLongPress,
  });

  @override
  State<_DayCell> createState() => _DayCellState();
}

class _DayCellState extends State<_DayCell>
    with SingleTickerProviderStateMixin {
  AnimationController? _c;

  @override
  void initState() {
    super.initState();
    if (widget.isToday) {
      _c = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 1400),
      )..repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(covariant _DayCell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.isToday != widget.isToday) {
      _c?.dispose();
      _c = null;
      if (widget.isToday) {
        _c = AnimationController(
          vsync: this,
          duration: const Duration(milliseconds: 1400),
        )..repeat(reverse: true);
      }
      setState(() {});
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  List<Widget> _inkDots(Color color, int count) {
    final dots = (count <= 0) ? 0 : (count == 1 ? 1 : (count == 2 ? 2 : 3));
    return List.generate(dots, (i) {
      return Container(
        width: 5,
        height: 5,
        margin: const EdgeInsets.only(right: 4),
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    final bg = widget.hasEntry
        ? scheme.primary.withValues(alpha: 0.12)
        : scheme.surface;

    final baseBorder = widget.isToday
        ? scheme.primary.withValues(alpha: 0.70)
        : scheme.outlineVariant.withValues(alpha: 0.35);

    final dotColor = scheme.primary.withValues(alpha: 0.85);

    Widget cell = Material(
      color: Colors.transparent,
      child: Ink(
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: baseBorder),
        ),
        child: Stack(
          children: [
            Center(
              child: Text(
                '${widget.day}',
                style: TextStyle(
                  fontWeight: FontWeight.w900,
                  color: widget.hasEntry
                      ? scheme.primary
                      : scheme.onSurface.withValues(alpha: 0.85),
                ),
              ),
            ),
            if (widget.hasEntry)
              Positioned(
                left: 0,
                right: 0,
                bottom: 6,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: _inkDots(dotColor, widget.count),
                ),
              ),
          ],
        ),
      ),
    );

    if (widget.isToday && _c != null) {
      cell = AnimatedBuilder(
        animation: _c!,
        builder: (_, child) {
          final glow = 0.10 + (_c!.value * 0.10);
          return DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: scheme.primary.withValues(alpha: glow),
                  blurRadius: 18,
                  spreadRadius: 1,
                ),
              ],
            ),
            child: child,
          );
        },
        child: cell,
      );
    }

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onTap,
      onLongPress: widget.onLongPress,
      child: cell,
    );
  }
}

// --------------------------
// Small internal helpers
// --------------------------

class _MonthSummary {
  final int daysWithEntries;
  final int totalEntries;
  final int streak;

  const _MonthSummary({
    required this.daysWithEntries,
    required this.totalEntries,
    required this.streak,
  });
}

/// Draft storage (simple, local)
class _DraftStore {
  static Future<String?> getString(String key) async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(key);
  }

  static Future<void> setString(String key, String value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(key, value);
  }

  static Future<void> remove(String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(key);
  }
}
