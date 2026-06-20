// lib/pages/habit_mindscore_screen.dart
//
// Combined Habit Tracking + MindScore display.
// Habit checkboxes update MindScore in real time.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:math';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/habit_service.dart';
import 'package:mindcore_ai/services/mindscore_service.dart';

class HabitMindScoreScreen extends StatefulWidget {
  const HabitMindScoreScreen({super.key});
  @override
  State<HabitMindScoreScreen> createState() => _HabitMindScoreScreenState();
}

class _HabitMindScoreScreenState extends State<HabitMindScoreScreen> {
  HabitEntry _habits = const HabitEntry(date: '');
  MindScoreResult _mindScore = MindScoreResult.empty;
  List<int> _trend = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final habits = await HabitService.getToday();
    final score = await MindScoreService.calculate();
    final trend = await MindScoreService.weeklyTrend();
    if (!mounted) return;
    setState(() {
      _habits = habits;
      _mindScore = score;
      _trend = trend;
      _loading = false;
    });
  }

  Future<void> _toggle(String habit) async {
    HapticFeedback.selectionClick();
    final updated = await HabitService.toggle(_habits, habit);
    final score = await MindScoreService.calculate();
    if (!mounted) return;
    setState(() {
      _habits = updated;
      _mindScore = score;
    });
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'MindScore'),
      body: AnimatedBackdrop(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
                children: [
                  // ── MindScore ring ─────────────────────────
                  GlassCard(
                    glowColor: _scoreColor(_mindScore.score).withValues(alpha: 0.15),
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      children: [
                        SizedBox(
                          width: 140, height: 140,
                          child: CustomPaint(
                            painter: _ScoreRingPainter(
                              score: _mindScore.score,
                              color: _scoreColor(_mindScore.score),
                              isDark: isDark,
                            ),
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    '${_mindScore.score}',
                                    style: tt.displaySmall?.copyWith(
                                      fontWeight: FontWeight.w900,
                                      color: _scoreColor(_mindScore.score),
                                    ),
                                  ),
                                  Text(
                                    'MindScore',
                                    style: tt.labelSmall?.copyWith(
                                      color: isDark
                                          ? Colors.white.withValues(alpha: 0.40)
                                          : Colors.black.withValues(alpha: 0.35),
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _scoreLabel(_mindScore.score),
                          style: tt.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                            color: _scoreColor(_mindScore.score),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _scoreSubtitle(_mindScore.score),
                          textAlign: TextAlign.center,
                          style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.45)
                                : const Color(0xFF475467),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // ── Weekly trend ───────────────────────────
                  if (_trend.isNotEmpty)
                    GlassCard(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('7-day trend', style: tt.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
                          const SizedBox(height: 14),
                          SizedBox(
                            height: 60,
                            child: CustomPaint(
                              size: const Size(double.infinity, 60),
                              painter: _TrendPainter(
                                values: _trend,
                                color: AppColors.primary,
                                isDark: isDark,
                              ),
                            ),
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text('6 days ago', style: tt.labelSmall?.copyWith(
                                  color: isDark ? Colors.white.withValues(alpha: 0.25) : Colors.black.withValues(alpha: 0.20))),
                              Text('Today', style: tt.labelSmall?.copyWith(
                                  color: isDark ? Colors.white.withValues(alpha: 0.25) : Colors.black.withValues(alpha: 0.20))),
                            ],
                          ),
                        ],
                      ),
                    ),
                  const SizedBox(height: 16),

                  // ── Daily habits ───────────────────────────
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 8),
                    child: Row(children: [
                      Icon(Icons.check_circle_outline_rounded, size: 14, color: AppColors.mintDeep),
                      const SizedBox(width: 6),
                      Text('TODAY\u2019S HABITS',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8,
                              color: isDark ? Colors.white.withValues(alpha: 0.45) : Colors.black.withValues(alpha: 0.40))),
                    ]),
                  ),
                  _HabitTile(icon: Icons.fitness_center_rounded, label: 'Exercise',
                      subtitle: 'Any physical activity today',
                      checked: _habits.exercise, onTap: () => _toggle('exercise'), isDark: isDark, tt: tt),
                  const SizedBox(height: 8),
                  _HabitTile(icon: Icons.water_drop_rounded, label: 'Hydration',
                      subtitle: 'Drank enough water',
                      checked: _habits.hydration, onTap: () => _toggle('hydration'), isDark: isDark, tt: tt),
                  const SizedBox(height: 8),
                  _HabitTile(icon: Icons.medication_rounded, label: 'Medication',
                      subtitle: 'Took prescribed medication or supplements',
                      checked: _habits.medication, onTap: () => _toggle('medication'), isDark: isDark, tt: tt),
                  const SizedBox(height: 8),
                  _HabitTile(icon: Icons.bedtime_rounded, label: 'Sleep',
                      subtitle: 'Got reasonable sleep last night',
                      checked: _habits.sleep, onTap: () => _toggle('sleep'), isDark: isDark, tt: tt),
                  const SizedBox(height: 20),

                  // ── Score breakdown ────────────────────────
                  Padding(
                    padding: const EdgeInsets.only(left: 4, bottom: 8),
                    child: Row(children: [
                      Icon(Icons.insights_rounded, size: 14, color: AppColors.violet),
                      const SizedBox(width: 6),
                      Text('SCORE BREAKDOWN',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8,
                              color: isDark ? Colors.white.withValues(alpha: 0.45) : Colors.black.withValues(alpha: 0.40))),
                    ]),
                  ),
                  GlassCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        _BreakdownRow(label: 'Mood', value: _mindScore.moodScore, weight: 30, isDark: isDark, tt: tt, color: AppColors.primary),
                        const SizedBox(height: 10),
                        _BreakdownRow(label: 'Habits', value: _mindScore.habitScore, weight: 25, isDark: isDark, tt: tt, color: AppColors.mintDeep),
                        const SizedBox(height: 10),
                        _BreakdownRow(label: 'Journal', value: _mindScore.journalScore, weight: 15, isDark: isDark, tt: tt, color: AppColors.violet),
                        const SizedBox(height: 10),
                        _BreakdownRow(label: 'Chat', value: _mindScore.chatScore, weight: 15, isDark: isDark, tt: tt, color: const Color(0xFFBA7517)),
                        const SizedBox(height: 10),
                        _BreakdownRow(label: 'Streak (${_mindScore.streak}d)', value: _mindScore.streakScore, weight: 15, isDark: isDark, tt: tt, color: const Color(0xFFE24B4A)),
                      ],
                    ),
                  ),
                ],
              ),
      ),
    );
  }

  Color _scoreColor(int score) {
    if (score >= 75) return AppColors.mintDeep;
    if (score >= 50) return AppColors.primary;
    if (score >= 25) return const Color(0xFFBA7517);
    return const Color(0xFFE24B4A);
  }

  String _scoreLabel(int score) {
    if (score >= 80) return 'Thriving';
    if (score >= 60) return 'On track';
    if (score >= 40) return 'Building momentum';
    if (score >= 20) return 'Getting started';
    return 'Day one counts';
  }

  String _scoreSubtitle(int score) {
    if (score >= 80) return 'You\u2019re showing up for yourself. Keep going.';
    if (score >= 60) return 'Consistent effort builds lasting change.';
    if (score >= 40) return 'Every check mark is a step forward.';
    if (score >= 20) return 'Small actions compound. You\u2019re doing it.';
    return 'You opened the app. That\u2019s already something.';
  }
}

// ── Habit toggle tile ────────────────────────────────────────────────────

class _HabitTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String subtitle;
  final bool checked;
  final VoidCallback onTap;
  final bool isDark;
  final TextTheme tt;

  const _HabitTile({
    required this.icon, required this.label, required this.subtitle,
    required this.checked, required this.onTap,
    required this.isDark, required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: checked
              ? AppColors.mintDeep.withValues(alpha: 0.08)
              : theme.colorScheme.surface,
          border: Border.all(
            color: checked
                ? AppColors.mintDeep.withValues(alpha: 0.30)
                : theme.dividerColor.withValues(alpha: 0.7),
            width: checked ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20,
                color: checked ? AppColors.mintDeep : (isDark ? Colors.white.withValues(alpha: 0.35) : Colors.black.withValues(alpha: 0.30))),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: tt.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: checked ? AppColors.mintDeep : null)),
                  Text(subtitle, style: tt.bodySmall?.copyWith(
                      color: isDark ? Colors.white.withValues(alpha: 0.35) : Colors.black.withValues(alpha: 0.35))),
                ],
              ),
            ),
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: checked
                  ? Icon(Icons.check_circle_rounded, color: AppColors.mintDeep, size: 24, key: const ValueKey(true))
                  : Icon(Icons.circle_outlined,
                      color: isDark ? Colors.white.withValues(alpha: 0.15) : Colors.black.withValues(alpha: 0.12),
                      size: 24, key: const ValueKey(false)),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Breakdown row ────────────────────────────────────────────────────────

class _BreakdownRow extends StatelessWidget {
  final String label;
  final double value;
  final int weight;
  final bool isDark;
  final TextTheme tt;
  final Color color;

  const _BreakdownRow({
    required this.label, required this.value, required this.weight,
    required this.isDark, required this.tt, required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(width: 90,
          child: Text(label, style: tt.bodySmall?.copyWith(fontWeight: FontWeight.w600))),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(
              height: 6,
              child: LinearProgressIndicator(
                value: (value / 100).clamp(0, 1),
                backgroundColor: isDark ? Colors.white.withValues(alpha: 0.06) : Colors.black.withValues(alpha: 0.05),
                valueColor: AlwaysStoppedAnimation<Color>(color),
              ),
            ),
          ),
        ),
        const SizedBox(width: 10),
        SizedBox(width: 40,
          child: Text('${value.round()}%',
              textAlign: TextAlign.right,
              style: tt.labelSmall?.copyWith(
                  color: isDark ? Colors.white.withValues(alpha: 0.45) : Colors.black.withValues(alpha: 0.40),
                  fontWeight: FontWeight.w700))),
      ],
    );
  }
}

// ── Score ring painter ───────────────────────────────────────────────────

class _ScoreRingPainter extends CustomPainter {
  final int score;
  final Color color;
  final bool isDark;

  _ScoreRingPainter({required this.score, required this.color, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 8;
    const strokeWidth = 10.0;

    // Background ring
    canvas.drawCircle(
      center, radius,
      Paint()
        ..color = isDark ? Colors.white.withValues(alpha: 0.06) : Colors.black.withValues(alpha: 0.05)
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth,
    );

    // Score arc
    final sweepAngle = (score / 100) * 2 * pi;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2, sweepAngle,
      false,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant _ScoreRingPainter old) =>
      old.score != score || old.color != color;
}

// ── Trend sparkline painter ──────────────────────────────────────────────

class _TrendPainter extends CustomPainter {
  final List<int> values;
  final Color color;
  final bool isDark;

  _TrendPainter({required this.values, required this.color, required this.isDark});

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final maxVal = values.reduce((a, b) => a > b ? a : b).clamp(1, 100);
    final stepX = size.width / (values.length - 1).clamp(1, 100);

    final path = Path();
    final dots = <Offset>[];

    for (int i = 0; i < values.length; i++) {
      final x = i * stepX;
      final y = size.height - (values[i] / maxVal * size.height * 0.85) - 4;
      dots.add(Offset(x, y));
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    // Line
    canvas.drawPath(
      path,
      Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeCap = StrokeCap.round
        ..strokeJoin = StrokeJoin.round,
    );

    // Dots
    for (final dot in dots) {
      canvas.drawCircle(dot, 3.5, Paint()..color = color);
      canvas.drawCircle(dot, 2, Paint()..color = isDark ? const Color(0xFF0C1622) : Colors.white);
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter old) => true;
}
