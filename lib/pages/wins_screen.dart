// lib/pages/wins_screen.dart
//
// Two daily questions + scrollable archive of past wins.
// Fast to complete — 30 seconds maximum.

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:mindcore_ai/services/wins_service.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class WinsScreen extends StatefulWidget {
  const WinsScreen({super.key});
  @override
  State<WinsScreen> createState() => _WinsScreenState();
}

class _WinsScreenState extends State<WinsScreen> {
  final _win1Controller = TextEditingController();
  final _win2Controller = TextEditingController();
  final _win1Focus      = FocusNode();
  final _win2Focus      = FocusNode();

  bool          _saving       = false;
  bool          _done         = false;
  bool          _alreadyDone  = false;
  DailyWin?     _todayWin;
  List<DailyWin> _recentWins = [];
  bool          _loadingWins = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _win1Controller.dispose();
    _win2Controller.dispose();
    _win1Focus.dispose();
    _win2Focus.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final today  = await WinsService.instance.getToday();
    final recent = await WinsService.instance.getRecent(days: 30);
    if (!mounted) return;
    setState(() {
      _todayWin    = today;
      _alreadyDone = today != null;
      _recentWins  = recent;
      _loadingWins = false;
    });
  }

  Future<void> _submit() async {
    final w1 = _win1Controller.text.trim();
    final w2 = _win2Controller.text.trim();
    if (w1.isEmpty && w2.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Add at least one win — even a small one counts.')));
      return;
    }
    if (_saving) return;
    setState(() => _saving = true);
    await WinsService.instance.saveToday(
      win1: w1.isNotEmpty ? w1 : '—',
      win2: w2.isNotEmpty ? w2 : '—',
    );
    if (!mounted) return;
    setState(() { _saving = false; _done = true; });
    await Future.delayed(const Duration(milliseconds: 900));
    // Reload and show archive
    await _load();
    if (mounted) setState(() { _done = false; _alreadyDone = true; });
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme  = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final tt     = theme.textTheme;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0A0E1A) : const Color(0xFFF5F7FF),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new,
              color: isDark ? Colors.white54 : Colors.black45),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text('Today\'s Wins',
            style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w800)),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Text('✨',
                  style: TextStyle(
                      fontSize: 20,
                      color: AppColors.primary.withValues(alpha: 0.80))),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: _done
            ? _buildDone(isDark, tt)
            : _loadingWins
                ? const Center(child: CircularProgressIndicator())
                : _buildContent(isDark, tt),
      ),
    );
  }

  Widget _buildDone(bool isDark, TextTheme tt) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 72, height: 72,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.mintDeep.withValues(alpha: 0.15),
              border: Border.all(color: AppColors.mintDeep, width: 2),
            ),
            child: const Icon(Icons.check_rounded, color: Color(0xFF4CAF82), size: 38),
          ),
          const SizedBox(height: 16),
          Text('Logged — well done.',
              style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text('Small wins add up.',
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.45))),
        ],
      ),
    );
  }

  Widget _buildContent(bool isDark, TextTheme tt) {
    final labelColor  = isDark ? Colors.white.withValues(alpha: 0.85) : Colors.black87;
    final subtleColor = isDark ? Colors.white.withValues(alpha: 0.40) : Colors.black.withValues(alpha: 0.40);

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
      children: [

        // ── Input section (hidden if already logged today) ──────────────
        if (!_alreadyDone) ...[
          const SizedBox(height: 8),
          Text(
            'What went okay today?',
            style: tt.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800, color: labelColor),
          ),
          const SizedBox(height: 6),
          Text('Even the smallest thing counts.',
              style: tt.bodyMedium?.copyWith(color: subtleColor)),
          const SizedBox(height: 28),

          _QuestionField(
            controller:  _win1Controller,
            focusNode:   _win1Focus,
            nextFocus:   _win2Focus,
            label:       'One thing that went okay today',
            hint:        'e.g. I got out of bed. I made a call I\'d been putting off.',
            isDark:      isDark,
            tt:          tt,
          ),
          const SizedBox(height: 20),
          _QuestionField(
            controller: _win2Controller,
            focusNode:  _win2Focus,
            label:      'One thing I did for myself today',
            hint:       'e.g. I ate properly. I stepped outside for 5 minutes.',
            isDark:     isDark,
            tt:         tt,
          ),
          const SizedBox(height: 28),

          SizedBox(
            height: 52,
            child: FilledButton(
              onPressed: _saving ? null : _submit,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.mintDeep,
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14)),
              ),
              child: _saving
                  ? const SizedBox(width: 22, height: 22,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Text('Log my wins',
                      style: TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            ),
          ),
          const SizedBox(height: 36),
        ],

        // ── Today's win (if already done) ────────────────────────
        if (_alreadyDone && _todayWin != null) ...[
          const SizedBox(height: 8),
          _WinDayCard(win: _todayWin!, isToday: true, isDark: isDark, tt: tt),
          const SizedBox(height: 24),
        ],

        // ── Archive ──────────────────────────────────────────────
        if (_recentWins.isNotEmpty) ...[
          Text('Your archive',
              style: tt.titleSmall?.copyWith(
                  fontWeight: FontWeight.w700, color: labelColor)),
          const SizedBox(height: 12),
          ..._recentWins
              .where((w) => !(_alreadyDone && w.date == _todayWin?.date))
              .map((w) => Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _WinDayCard(
                        win: w, isToday: false, isDark: isDark, tt: tt),
                  )),
        ] else if (_alreadyDone) ...[
          Center(
            child: Text('Your wins will build up here over time.',
                style: tt.bodySmall?.copyWith(color: subtleColor),
                textAlign: TextAlign.center),
          ),
        ],
      ],
    );
  }
}

// ── Input field ────────────────────────────────────────────────────────────

class _QuestionField extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode             focusNode;
  final FocusNode?            nextFocus;
  final String                label;
  final String                hint;
  final bool                  isDark;
  final TextTheme             tt;

  const _QuestionField({
    required this.controller,
    required this.focusNode,
    this.nextFocus,
    required this.label,
    required this.hint,
    required this.isDark,
    required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: tt.bodyMedium?.copyWith(
                fontWeight: FontWeight.w700,
                color: isDark ? Colors.white.withValues(alpha: 0.85) : Colors.black87)),
        const SizedBox(height: 8),
        TextField(
          controller: controller,
          focusNode:  focusNode,
          maxLines:   3,
          maxLength:  200,
          textInputAction:
              nextFocus != null ? TextInputAction.next : TextInputAction.done,
          onSubmitted: (_) {
            if (nextFocus != null) FocusScope.of(context).requestFocus(nextFocus);
          },
          style: TextStyle(
              color: isDark ? Colors.white : Colors.black87, fontSize: 15),
          decoration: InputDecoration(
            hintText:    hint,
            hintStyle:   TextStyle(color: isDark
                ? Colors.white.withValues(alpha: 0.30)
                : Colors.black.withValues(alpha: 0.30), fontSize: 14),
            counterStyle: TextStyle(color: isDark
                ? Colors.white.withValues(alpha: 0.30)
                : Colors.black.withValues(alpha: 0.30), fontSize: 11),
            filled:    true,
            fillColor: isDark
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.black.withValues(alpha: 0.04),
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
        ),
      ],
    );
  }
}

// ── Win day card ───────────────────────────────────────────────────────────

class _WinDayCard extends StatelessWidget {
  final DailyWin  win;
  final bool      isToday;
  final bool      isDark;
  final TextTheme tt;

  const _WinDayCard({
    required this.win,
    required this.isToday,
    required this.isDark,
    required this.tt,
  });

  String _formatDate(String date) {
    try {
      final d = DateTime.parse(date);
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final winDay = DateTime(d.year, d.month, d.day);
      final diff = today.difference(winDay).inDays;
      if (diff == 0) return 'Today';
      if (diff == 1) return 'Yesterday';
      return DateFormat('EEE, MMM d').format(d);
    } catch (_) { return date; }
  }

  @override
  Widget build(BuildContext context) {
    final accent = isToday ? AppColors.mintDeep : AppColors.primary;
    final cardColor = isDark
        ? Colors.white.withValues(alpha: 0.05)
        : Colors.black.withValues(alpha: 0.03);
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.10)
        : Colors.black.withValues(alpha: 0.08);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 8, height: 8,
                decoration: BoxDecoration(
                    shape: BoxShape.circle, color: accent),
              ),
              const SizedBox(width: 8),
              Text(
                _formatDate(win.date),
                style: tt.labelMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: accent),
              ),
            ],
          ),
          if (win.win1.isNotEmpty && win.win1 != '—') ...[
            const SizedBox(height: 10),
            _WinRow(
              icon:   Icons.check_circle_outline_rounded,
              text:   win.win1,
              isDark: isDark, tt: tt,
            ),
          ],
          if (win.win2.isNotEmpty && win.win2 != '—') ...[
            const SizedBox(height: 8),
            _WinRow(
              icon:   Icons.favorite_border_rounded,
              text:   win.win2,
              isDark: isDark, tt: tt,
            ),
          ],
        ],
      ),
    );
  }
}

class _WinRow extends StatelessWidget {
  final IconData  icon;
  final String    text;
  final bool      isDark;
  final TextTheme tt;
  const _WinRow({required this.icon, required this.text,
      required this.isDark, required this.tt});
  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(top: 1),
          child: Icon(icon, size: 15,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : Colors.black.withValues(alpha: 0.40)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(text,
              style: tt.bodyMedium?.copyWith(
                  height: 1.45,
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.80)
                      : Colors.black.withValues(alpha: 0.75))),
        ),
      ],
    );
  }
}
