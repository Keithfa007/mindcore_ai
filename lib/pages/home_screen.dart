// lib/pages/home_screen.dart
import 'package:flutter/material.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/surfaces.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/animated_logo.dart';
import 'package:mindcore_ai/widgets/mood_prediction_chip.dart';
import 'package:mindcore_ai/widgets/streak_badge.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/ai/daily_briefing_service.dart';
import 'package:mindcore_ai/ai/mood_pattern_service.dart';
import 'package:mindcore_ai/ai/weekly_report_service.dart';
import 'package:mindcore_ai/services/streak_service.dart';

import 'package:mindcore_ai/pages/helpers/journal_service.dart';
import 'package:mindcore_ai/services/daily_plan_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';
import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with TickerProviderStateMixin {
  final TextEditingController _plan = TextEditingController();
  bool _savingPlan = false;

  List<double> _last7 = const [];
  ProactiveSuggestion? _supportSuggestion;

  String? _briefing;
  bool _briefingLoading = true;
  MoodPrediction? _prediction;
  WeeklyReport? _weeklyReport;
  int _streak = 0;

  // Staggered entrance — 7 cards now (Daily Reset removed)
  late final AnimationController _entranceCtrl;
  final List<Animation<double>> _fadeAnims  = [];
  final List<Animation<Offset>> _slideAnims = [];
  static const int _cardCount = 7;

  @override
  void initState() {
    super.initState();
    _entranceCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 950),
    );
    for (int i = 0; i < _cardCount; i++) {
      final start    = (i * 0.10).clamp(0.0, 0.88);
      final end      = (start + 0.36).clamp(0.0, 1.0);
      final interval = Interval(start, end, curve: Curves.easeOut);
      _fadeAnims.add(
        Tween<double>(begin: 0.0, end: 1.0)
            .animate(CurvedAnimation(parent: _entranceCtrl, curve: interval)),
      );
      _slideAnims.add(
        Tween<Offset>(begin: const Offset(0, 0.06), end: Offset.zero)
            .animate(CurvedAnimation(parent: _entranceCtrl, curve: interval)),
      );
    }
    _loadAll();
    _loadAI();
    _entranceCtrl.forward();
  }

  @override
  void dispose() {
    _plan.dispose();
    _entranceCtrl.dispose();
    super.dispose();
  }

  Widget _animated(int index, Widget child) {
    if (index >= _fadeAnims.length) return child;
    return FadeTransition(
      opacity: _fadeAnims[index],
      child: SlideTransition(position: _slideAnims[index], child: child),
    );
  }

  Future<void> _loadAI() async {
    setState(() => _briefingLoading = true);
    final results = await Future.wait([
      DailyBriefingService.getBriefing(),
      MoodPatternService.detect(),
      WeeklyReportService.getReport(),
      StreakService.currentStreak(),
    ]);
    if (!mounted) return;
    setState(() {
      _briefing        = results[0] as String?;
      _prediction      = results[1] as MoodPrediction?;
      _weeklyReport    = results[2] as WeeklyReport?;
      _streak          = results[3] as int? ?? 0;
      _briefingLoading = false;
    });
  }

  Future<void> _loadAll() async {
    await DailyPlanService.getTodayNote();
    final mood       = await MoodRepo.instance.last7Normalized();
    final suggestion = await ProactiveSupportService.buildHomeSuggestion();
    final reminderEnabled = await SettingsService.getDailyReminderEnabled();
    final reminderTime    = await SettingsService.getDailyReminderTime();

    if (reminderEnabled) {
      await NotificationService.instance
          .scheduleDailyRecommendationNotification(
        uniqueKey: suggestion.id,
        title: suggestion.notificationTitle,
        body: suggestion.notificationBody,
        routeName: suggestion.routeName,
        routeArguments: suggestion.routeArguments,
        hour: reminderTime.hour,
        minute: reminderTime.minute,
      );
    }

    if (!mounted) return;
    setState(() {
      _plan.text         = '';
      _last7             = mood;
      _supportSuggestion = suggestion;
    });
  }

  Future<void> _saveJournal() async {
    final text = _plan.text.trim();
    if (_savingPlan) return;
    if (text.isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Write something first.')));
      return;
    }
    setState(() => _savingPlan = true);
    await JournalService.addEntry(text, when: DateTime.now());
    if (!mounted) return;
    setState(() => _savingPlan = false);
    _plan.clear();
    FocusScope.of(context).unfocus();
    await _loadAll();
    // Refresh mood pattern after new journal entry
    final newPrediction = await MoodPatternService.refresh();
    if (mounted) setState(() => _prediction = newPrediction);
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Journal entry saved.')));
  }

  void _openRecommendation() {
    final s = _supportSuggestion;
    if (s == null) return;
    Navigator.of(context).pushNamed(s.routeName, arguments: s.routeArguments);
  }

  Future<void> _openPremiumRoute(String route) async {
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      return;
    }
    Navigator.of(context).pushNamed(route);
  }

  String get _greeting {
    final h = DateTime.now().hour;
    if (h >= 5  && h < 9)  return 'Early start';
    if (h >= 9  && h < 12) return 'Good morning';
    if (h >= 12 && h < 17) return 'Good afternoon';
    if (h >= 17 && h < 21) return 'Good evening';
    return 'Good night';
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      title: 'MindCore AI',
      bottomIndex: 0,
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
          children: [

            // 0 ─ Hero
            _animated(0, Padding(
              padding: const EdgeInsets.fromLTRB(0, 28, 0, 8),
              child: Column(
                children: [
                  const AnimatedLogo(size: 160),
                  const SizedBox(height: 16),
                  StreakBadge(streak: _streak),
                  const SizedBox(height: 14),
                  Text(
                    _greeting,
                    style: tt.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: isDark ? Colors.white : const Color(0xFF0E1320),
                      letterSpacing: -0.8,
                    ),
                  ),
                  const SizedBox(height: 10),
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 500),
                    child: _briefingLoading
                        ? _BriefingShimmer(isDark: isDark)
                        : _BriefingText(
                            text: _briefing ?? '', isDark: isDark, tt: tt),
                  ),
                ],
              ),
            )),
            const SizedBox(height: 20),

            // 1 ─ SOS
            _animated(1, Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _SosButton(
                onTap: () => Navigator.of(context).pushNamed('/sos'),
                isDark: isDark, tt: tt,
              ),
            )),

            // 2 ─ Mood insight chip (AI-powered, only shows with real data)
            if (_prediction != null)
              _animated(2, Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: MoodPredictionChip(
                  prediction: _prediction!,
                  onAction: _prediction!.actionRoute != null
                      ? () => _openPremiumRoute(_prediction!.actionRoute!)
                      : null,
                ),
              )),

            // 3 ─ Weekly report
            if (_weeklyReport != null)
              _animated(3, Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _WeeklyReportCard(
                    report: _weeklyReport!, tt: tt, isDark: isDark),
              )),

            // 4 ─ Chat buttons
            _animated(4, Row(
              children: [
                Expanded(
                  child: GlassCard(
                    glowColor: AppColors.glowBlue,
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        Container(
                          width: 50, height: 50,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [Color(0xFF4D7CFF), Color(0xFF74C3FF)],
                            ),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.primary.withValues(alpha: 0.35),
                                blurRadius: 16, offset: const Offset(0, 6),
                              )
                            ],
                          ),
                          child: const Icon(Icons.chat_rounded,
                              color: Colors.white, size: 24),
                        ),
                        const SizedBox(height: 10),
                        Text('Text Chat',
                            style: tt.titleSmall
                                ?.copyWith(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        Text('Type your thoughts',
                            style: tt.bodySmall?.copyWith(
                                color: cs.onSurface.withValues(alpha: 0.55)),
                            textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: () =>
                                Navigator.of(context).pushNamed('/chat'),
                            style: FilledButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 10)),
                            child: const Text('Open'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: GlassCard(
                    glowColor: AppColors.glowMint,
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        Container(
                          width: 50, height: 50,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                              colors: [
                                Color(0xFF32D0BE), Color(0xFF89E0CF)
                              ],
                            ),
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: AppColors.mintDeep
                                    .withValues(alpha: 0.35),
                                blurRadius: 16,
                                offset: const Offset(0, 6),
                              )
                            ],
                          ),
                          child: const Icon(Icons.mic_rounded,
                              color: Colors.white, size: 24),
                        ),
                        const SizedBox(height: 10),
                        Text('Voice Chat',
                            style: tt.titleSmall
                                ?.copyWith(fontWeight: FontWeight.w800)),
                        const SizedBox(height: 4),
                        Text('Speak hands-free',
                            style: tt.bodySmall?.copyWith(
                                color: cs.onSurface.withValues(alpha: 0.55)),
                            textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: () => Navigator.of(context)
                                .pushNamed('/voice-chat'),
                            style: FilledButton.styleFrom(
                              padding:
                                  const EdgeInsets.symmetric(vertical: 10),
                              backgroundColor: AppColors.mintDeep,
                              foregroundColor: Colors.white,
                            ),
                            child: const Text('Open'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            )),
            const SizedBox(height: 12),

            // 5 ─ Guided sessions
            _animated(5, ValueListenableBuilder<bool>(
              valueListenable: PremiumService.isPremium,
              builder: (context, isPremium, _) {
                return GlassCard(
                  glowColor: AppColors.glowViolet,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Guided Sessions',
                        subtitle:
                            'Ready-to-play calming audio journeys for focus, sleep, panic, and emotional reset',
                      ),
                      const SizedBox(height: 10),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: () =>
                              _openPremiumRoute('/guided-sessions'),
                          icon: Icon(isPremium
                              ? Icons.self_improvement_rounded
                              : Icons.lock_rounded),
                          label: Text(isPremium
                              ? 'Open Guided Sessions'
                              : 'Unlock Guided Sessions'),
                        ),
                      ),
                    ],
                  ),
                );
              },
            )),
            const SizedBox(height: 12),

            // 6 ─ Recommended for you
            if (_supportSuggestion != null)
              _animated(6, GlassCard(
                glowColor: AppColors.glowMint,
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeroCard(
                      title: 'Recommended for you',
                      subtitle:
                          'A gentle nudge based on your recent activity',
                    ),
                    const SizedBox(height: 12),
                    NestCard(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(_supportSuggestion!.icon, size: 22),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _supportSuggestion!.title,
                                  style: tt.titleSmall?.copyWith(
                                      fontWeight: FontWeight.w700),
                                ),
                                const SizedBox(height: 6),
                                Text(_supportSuggestion!.subtitle),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _openRecommendation,
                        icon: Icon(_supportSuggestion!.icon, size: 18),
                        label: Text(_supportSuggestion!.ctaLabel),
                      ),
                    ),
                  ],
                ),
              )),
            if (_supportSuggestion != null) const SizedBox(height: 12),

            // Journal (no animation wrapper — always visible)
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(
                      title: 'Journal',
                      subtitle: 'You can write anything here.'),
                  const SizedBox(height: 12),
                  NestCard(
                    child: TextField(
                      controller: _plan,
                      maxLines: 4,
                      textInputAction: TextInputAction.newline,
                      decoration: const InputDecoration(
                        hintText: 'A few lines is enough\u2026',
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  ValueListenableBuilder<bool>(
                    valueListenable: PremiumService.isPremium,
                    builder: (context, isPremium, _) {
                      return Row(
                        children: [
                          Expanded(
                            child: FilledButton(
                              onPressed: _savingPlan ? null : _saveJournal,
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 12.0),
                                child: Text(
                                    _savingPlan ? 'Saving\u2026' : 'Save entry'),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          OutlinedButton.icon(
                            onPressed: () => _openPremiumRoute('/daily-hub'),
                            icon: Icon(
                              isPremium
                                  ? Icons.visibility_rounded
                                  : Icons.lock_rounded,
                              size: 16,
                            ),
                            label: const Padding(
                              padding: EdgeInsets.symmetric(vertical: 12.0),
                              child: Text('View'),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Saved locally on your device.',
                    style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.45)
                          : Colors.black.withValues(alpha: 0.45),
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
}

// ── SOS button ────────────────────────────────────────────────────────────────────

class _SosButton extends StatelessWidget {
  final VoidCallback onTap;
  final bool isDark;
  final TextTheme tt;
  const _SosButton(
      {required this.onTap, required this.isDark, required this.tt});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding:
            const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: const Color(0xFFFF6B6B)
                .withValues(alpha: isDark ? 0.55 : 0.40),
            width: 1.5,
          ),
          color: const Color(0xFFFF6B6B)
              .withValues(alpha: isDark ? 0.10 : 0.07),
          boxShadow: [
            BoxShadow(
              color: const Color(0xFFFF6B6B).withValues(alpha: 0.18),
              blurRadius: 18, spreadRadius: 1,
            )
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 38, height: 38,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFFFF6B6B).withValues(alpha: 0.15),
              ),
              child: const Icon(Icons.warning_amber_rounded,
                  color: Color(0xFFFF6B6B), size: 20),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'SOS \u2014 I need help right now',
                    style: tt.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: const Color(0xFFFF6B6B),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    'Tap for instant grounding: breathe, ground, audio',
                    style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.50)
                          : Colors.black.withValues(alpha: 0.50),
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right_rounded,
              color: const Color(0xFFFF6B6B).withValues(alpha: 0.70),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}

// ── Weekly report card ─────────────────────────────────────────────────────────

class _WeeklyReportCard extends StatelessWidget {
  final WeeklyReport report;
  final TextTheme tt;
  final bool isDark;
  const _WeeklyReportCard(
      {required this.report, required this.tt, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      glowColor: AppColors.glowViolet,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.violet.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: AppColors.violet.withValues(alpha: 0.35)),
            ),
            child: Text('Weekly Report',
                style: tt.labelSmall?.copyWith(
                    color: AppColors.violet,
                    fontWeight: FontWeight.w800)),
          ),
          const SizedBox(height: 12),
          Text(
            report.summary,
            style: tt.bodyMedium?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.85)
                  : const Color(0xFF0E1320),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 14),
          _ReportRow(
              icon: Icons.star_rounded,
              color: AppColors.mintDeep,
              label: 'Best day',
              value: report.bestDay,
              tt: tt, isDark: isDark),
          const SizedBox(height: 8),
          _ReportRow(
              icon: Icons.lightbulb_rounded,
              color: AppColors.primary,
              label: 'What helped',
              value: report.highlight,
              tt: tt, isDark: isDark),
          const SizedBox(height: 8),
          _ReportRow(
              icon: Icons.visibility_rounded,
              color: AppColors.violet,
              label: 'Watch out',
              value: report.watchOut,
              tt: tt, isDark: isDark),
        ],
      ),
    );
  }
}

class _ReportRow extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  final String value;
  final TextTheme tt;
  final bool isDark;
  const _ReportRow({
    required this.icon, required this.color, required this.label,
    required this.value, required this.tt, required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color, size: 16),
        const SizedBox(width: 8),
        Expanded(
          child: RichText(
            text: TextSpan(
              style: tt.bodySmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.65)
                    : const Color(0xFF475467),
                height: 1.4,
              ),
              children: [
                TextSpan(
                    text: '$label: ',
                    style: const TextStyle(fontWeight: FontWeight.w800)),
                TextSpan(text: value),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// ── Briefing shimmer ───────────────────────────────────────────────────────────────

class _BriefingShimmer extends StatefulWidget {
  final bool isDark;
  const _BriefingShimmer({required this.isDark});
  @override
  State<_BriefingShimmer> createState() => _BriefingShimmerState();
}

class _BriefingShimmerState extends State<_BriefingShimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1200))
      ..repeat(reverse: true);
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        final alpha = 0.08 + _anim.value * 0.12;
        return Column(children: [
          Container(
            width: 240, height: 13,
            decoration: BoxDecoration(
              color: (widget.isDark ? Colors.white : Colors.black)
                  .withValues(alpha: alpha),
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(height: 6),
          Container(
            width: 180, height: 11,
            decoration: BoxDecoration(
              color: (widget.isDark ? Colors.white : Colors.black)
                  .withValues(alpha: alpha * 0.7),
              borderRadius: BorderRadius.circular(6),
            ),
          ),
        ]);
      },
    );
  }
}

// ── Briefing text ───────────────────────────────────────────────────────────────

class _BriefingText extends StatelessWidget {
  final String text;
  final bool isDark;
  final TextTheme tt;
  const _BriefingText(
      {required this.text, required this.isDark, required this.tt});

  @override
  Widget build(BuildContext context) {
    if (text.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Text(
        text,
        textAlign: TextAlign.center,
        style: tt.bodyMedium?.copyWith(
          color: isDark
              ? Colors.white.withValues(alpha: 0.65)
              : const Color(0xFF475467),
          height: 1.5,
          letterSpacing: 0.1,
        ),
      ),
    );
  }
}
