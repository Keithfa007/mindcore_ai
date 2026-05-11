// lib/pages/journey_screen.dart
//
// Personal growth screen — shows the user their real progress over time.
// Built entirely from existing MoodRepo and StreakService data.
// Accessed from the evolved home screen insight card.

import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/journey_service.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/gradient_background.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';

class JourneyScreen extends StatefulWidget {
  const JourneyScreen({super.key});
  @override
  State<JourneyScreen> createState() => _JourneyScreenState();
}

class _JourneyScreenState extends State<JourneyScreen> {
  WeeklyStats?   _stats;
  MonthlyTrend?  _trend;
  List<Milestone> _milestones = [];
  String         _insight = '';
  bool           _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final results = await Future.wait([
      JourneyService.getWeeklyStats(),
      JourneyService.getMonthlyTrend(),
      JourneyService.getMilestones(),
    ]);
    final stats      = results[0] as WeeklyStats;
    final trend      = results[1] as MonthlyTrend;
    final milestones = results[2] as List<Milestone>;
    // Load insight in background — don't block the screen
    if (!mounted) return;
    setState(() {
      _stats      = stats;
      _trend      = trend;
      _milestones = milestones;
      _loading    = false;
    });
    // Fetch AI insight after UI is visible
    final insight = await JourneyService.getWeeklyInsight(stats);
    if (mounted) setState(() => _insight = insight);
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppTopBar(
        title: 'Your Journey',
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: GradientBackground(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                children: [
                  _buildThisWeek(tt, cs, isDark),
                  const SizedBox(height: 12),
                  if (_insight.isNotEmpty) _buildInsight(tt, cs, isDark),
                  if (_insight.isNotEmpty) const SizedBox(height: 12),
                  _buildMonthlyTrend(tt, cs, isDark),
                  const SizedBox(height: 12),
                  if (_milestones.isNotEmpty) _buildMilestones(tt, cs, isDark),
                ],
              ),
      ),
    );
  }

  // ── This week ───────────────────────────────────────────────────────────────

  Widget _buildThisWeek(TextTheme tt, ColorScheme cs, bool isDark) {
    final s = _stats!;
    final hasData = s.thisWeekAvg > 0;
    final score   = (s.thisWeekAvg * 2).toStringAsFixed(1);

    return GlassCard(
      glowColor: AppColors.glowBlue,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: AppColors.primary.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(100),
                ),
                child: Text('This Week',
                    style: tt.labelSmall?.copyWith(
                        color: AppColors.primary, fontWeight: FontWeight.w800)),
              ),
              const Spacer(),
              if (s.streak > 0)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: AppColors.mintDeep.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(100),
                  ),
                  child: Text('🔥 ${s.streak}-day streak',
                      style: tt.labelSmall?.copyWith(
                          color: AppColors.mintDeep, fontWeight: FontWeight.w800)),
                ),
            ],
          ),
          const SizedBox(height: 16),
          if (!hasData)
            Text('Log your mood today to start tracking your journey.',
                style: tt.bodyMedium?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.55)
                        : const Color(0xFF475467)))
          else ...[  
            Row(
              children: [
                Expanded(
                  child: _StatBox(
                    label: 'Mood avg',
                    value: '$score / 10',
                    sub: s.trendEmoji,
                    color: AppColors.primary,
                    tt: tt, isDark: isDark,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _StatBox(
                    label: 'Check-ins',
                    value: '${s.checkInsThisWeek}',
                    sub: 'this week',
                    color: AppColors.mintDeep,
                    tt: tt, isDark: isDark,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _StatBox(
                    label: 'vs last week',
                    value: s.lastWeekAvg > 0
                        ? (s.thisWeekAvg - s.lastWeekAvg >= 0 ? '+' : '') +
                          ((s.thisWeekAvg - s.lastWeekAvg) * 2).toStringAsFixed(1)
                        : '—',
                    sub: s.trendEmoji,
                    color: s.thisWeekAvg >= s.lastWeekAvg
                        ? AppColors.mintDeep
                        : const Color(0xFFFF6B6B),
                    tt: tt, isDark: isDark,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  // ── AI insight ────────────────────────────────────────────────────────────────

  Widget _buildInsight(TextTheme tt, ColorScheme cs, bool isDark) {
    return GlassCard(
      glowColor: AppColors.glowViolet,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text('🧠', style: TextStyle(fontSize: 18)),
              const SizedBox(width: 8),
              Text('Your Week',
                  style: tt.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: isDark ? Colors.white : const Color(0xFF0E1320))),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            _insight,
            style: tt.bodyMedium?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.85)
                  : const Color(0xFF0E1320),
              height: 1.55,
            ),
          ),
          const SizedBox(height: 8),
          Text('Refreshes every Sunday',
              style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.35)
                      : const Color(0xFF94A3B8))),
        ],
      ),
    );
  }

  // ── Monthly trend chart ───────────────────────────────────────────────────────

  Widget _buildMonthlyTrend(TextTheme tt, ColorScheme cs, bool isDark) {
    final trend = _trend!;
    final weeks = trend.weeks;
    final hasAnyData = weeks.any((v) => v > 0);
    final labels = ['3w ago', '2w ago', 'Last week', 'This week'];

    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('4-Week Mood Trend',
              style: tt.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 4),
          Text(trend.monthLabel,
              style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.40)
                      : const Color(0xFF94A3B8))),
          const SizedBox(height: 20),
          if (!hasAnyData)
            Text('Keep logging your mood and your trend will appear here.',
                style: tt.bodyMedium?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.55)
                        : const Color(0xFF475467)))
          else
            SizedBox(
              height: 120,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: List.generate(4, (i) {
                  final val   = weeks[i];
                  final isMax = val == weeks.reduce((a, b) => a > b ? a : b) && val > 0;
                  return Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          if (val > 0)
                            Text(
                              (val * 10).toStringAsFixed(1),
                              style: tt.labelSmall?.copyWith(
                                  color: isMax
                                      ? AppColors.mintDeep
                                      : cs.onSurface.withValues(alpha: 0.55),
                                  fontWeight: FontWeight.w700),
                            ),
                          const SizedBox(height: 4),
                          AnimatedContainer(
                            duration: const Duration(milliseconds: 600),
                            curve: Curves.easeOut,
                            height: val > 0 ? (val * 90).clamp(6.0, 90.0) : 6,
                            decoration: BoxDecoration(
                              borderRadius: const BorderRadius.vertical(
                                  top: Radius.circular(6)),
                              color: val > 0
                                  ? (isMax
                                      ? AppColors.mintDeep
                                      : AppColors.primary.withValues(alpha: 0.65))
                                  : cs.onSurface.withValues(alpha: 0.08),
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(labels[i],
                              style: tt.bodySmall?.copyWith(
                                  fontSize: 10,
                                  color: cs.onSurface.withValues(alpha: 0.50)),
                              textAlign: TextAlign.center),
                        ],
                      ),
                    ),
                  );
                }),
              ),
            ),
        ],
      ),
    );
  }

  // ── Milestones ───────────────────────────────────────────────────────────────

  Widget _buildMilestones(TextTheme tt, ColorScheme cs, bool isDark) {
    return GlassCard(
      glowColor: AppColors.glowMint,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Milestones',
              style: tt.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 12),
          ..._milestones.map((m) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Row(
              children: [
                Text(m.emoji, style: const TextStyle(fontSize: 24)),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(m.title,
                          style: tt.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: isDark
                                  ? Colors.white
                                  : const Color(0xFF0E1320))),
                      Text(m.subtitle,
                          style: tt.bodySmall?.copyWith(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.55)
                                  : const Color(0xFF475467))),
                    ],
                  ),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }
}

// ── Stat box widget ───────────────────────────────────────────────────────────────────

class _StatBox extends StatelessWidget {
  final String label;
  final String value;
  final String sub;
  final Color  color;
  final TextTheme tt;
  final bool isDark;
  const _StatBox({
    required this.label, required this.value, required this.sub,
    required this.color, required this.tt, required this.isDark,
  });
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.18)),
      ),
      child: Column(
        children: [
          Text(value,
              style: tt.titleMedium?.copyWith(
                  fontWeight: FontWeight.w900, color: color)),
          const SizedBox(height: 2),
          Text(sub,
              style: tt.bodySmall?.copyWith(
                  color: color.withValues(alpha: 0.75)),
              textAlign: TextAlign.center),
          const SizedBox(height: 4),
          Text(label,
              style: tt.bodySmall?.copyWith(
                  fontSize: 10,
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : const Color(0xFF94A3B8)),
              textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
