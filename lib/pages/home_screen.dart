import 'package:flutter/material.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/surfaces.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/mood_orb.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/ai/daily_briefing_service.dart';

import 'package:mindcore_ai/pages/helpers/journal_service.dart';

import 'package:mindcore_ai/services/daily_plan_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';
import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';
import 'package:mindcore_ai/widgets/tts_replay_button.dart';
import 'package:mindcore_ai/widgets/tts_speaker_button.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with AutoStopTtsRouteAware<HomeScreen>, TickerProviderStateMixin {
  final TextEditingController _plan = TextEditingController();
  bool _savingPlan = false;

  List<double> _last7 = const [];
  ProactiveSuggestion? _supportSuggestion;

  // AI daily briefing
  String? _briefing;
  bool _briefingLoading = true;

  // Staggered entrance animations
  late final AnimationController _entranceCtrl;
  final List<Animation<double>> _fadeAnims = [];
  final List<Animation<Offset>> _slideAnims = [];
  static const int _cardCount = 6;

  @override
  void initState() {
    super.initState();

    _entranceCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );

    for (int i = 0; i < _cardCount; i++) {
      final start = (i * 0.12).clamp(0.0, 0.9);
      final end = (start + 0.40).clamp(0.0, 1.0);
      final interval = Interval(start, end, curve: Curves.easeOut);
      _fadeAnims.add(
        Tween<double>(begin: 0.0, end: 1.0).animate(
          CurvedAnimation(parent: _entranceCtrl, curve: interval),
        ),
      );
      _slideAnims.add(
        Tween<Offset>(
          begin: const Offset(0, 0.06),
          end: Offset.zero,
        ).animate(
          CurvedAnimation(parent: _entranceCtrl, curve: interval),
        ),
      );
    }

    _loadAll();
    _loadBriefing();
    _entranceCtrl.forward();
  }

  @override
  void dispose() {
    _plan.dispose();
    _entranceCtrl.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  Widget _animated(int index, Widget child) {
    if (index >= _fadeAnims.length) return child;
    return FadeTransition(
      opacity: _fadeAnims[index],
      child: SlideTransition(position: _slideAnims[index], child: child),
    );
  }

  // ── Load AI briefing ───────────────────────────────────────
  Future<void> _loadBriefing() async {
    setState(() => _briefingLoading = true);
    final text = await DailyBriefingService.getBriefing();
    if (!mounted) return;
    setState(() {
      _briefing = text;
      _briefingLoading = false;
    });
  }

  // ── Load mood + suggestion ─────────────────────────────────
  Future<void> _loadAll() async {
    await DailyPlanService.getTodayNote();
    final mood = await MoodRepo.instance.last7Normalized();
    final suggestion = await ProactiveSupportService.buildHomeSuggestion();
    final reminderEnabled = await SettingsService.getDailyReminderEnabled();
    final reminderTime = await SettingsService.getDailyReminderTime();

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
      _plan.text = '';
      _last7 = mood;
      _supportSuggestion = suggestion;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final autoSpeakText = suggestion.subtitle.trim().isNotEmpty
          ? '${suggestion.title}. ${suggestion.subtitle.split('.').first.trim()}'
          : suggestion.title;
      await OpenAiTtsService.instance.maybeSpeakOncePerDay(
        uniqueKey: suggestion.id,
        text: autoSpeakText,
        surface: TtsSurface.recommendation,
        moodLabel: 'calm',
        messageId: 'home_recommendation_${suggestion.id}',
      );
    });
  }

  Future<void> _saveJournal() async {
    final text = _plan.text.trim();
    if (_savingPlan) return;
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Write something first.')),
      );
      return;
    }
    setState(() => _savingPlan = true);
    await JournalService.addEntry(text, when: DateTime.now());
    if (!mounted) return;
    setState(() => _savingPlan = false);
    _plan.clear();
    FocusScope.of(context).unfocus();
    await _loadAll();
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Journal entry saved.')),
    );
  }

  void _openRecommendation() {
    final suggestion = _supportSuggestion;
    if (suggestion == null) return;
    Navigator.of(context).pushNamed(
      suggestion.routeName,
      arguments: suggestion.routeArguments,
    );
  }

  Future<void> _openPremiumRoute(String route) async {
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      return;
    }
    Navigator.of(context).pushNamed(route);
  }

  // ── Time-aware greeting ───────────────────────────────────
  String get _greeting {
    final hour = DateTime.now().hour;
    if (hour >= 5 && hour < 9) return 'Early start';
    if (hour >= 9 && hour < 12) return 'Good morning';
    if (hour >= 12 && hour < 17) return 'Good afternoon';
    if (hour >= 17 && hour < 21) return 'Good evening';
    return 'Good night';
  }

  // ── Orb colour from mood average ──────────────────────────
  Color get _orbColor {
    if (_last7.isEmpty) return AppColors.primary;
    final nonZero = _last7.where((v) => v > 0).toList();
    if (nonZero.isEmpty) return AppColors.primary;
    final avg = nonZero.reduce((a, b) => a + b) / nonZero.length;
    if (avg >= 0.65) return AppColors.mintDeep; // good — teal
    if (avg >= 0.40) return AppColors.primary;   // neutral — blue
    return AppColors.violet;                     // low — soft violet
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      title: 'MindCore AI',
      bottomIndex: 0,
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 32),
          children: [

            // ── Hero Orb + Greeting + AI Briefing ─────────────────
            _animated(
              0,
              Padding(
                padding: const EdgeInsets.fromLTRB(0, 28, 0, 8),
                child: Column(
                  children: [
                    MoodOrb(moodColor: _orbColor, size: 160),
                    const SizedBox(height: 20),

                    // Greeting
                    Text(
                      _greeting,
                      style: tt.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                        color: isDark
                            ? Colors.white
                            : const Color(0xFF0E1320),
                        letterSpacing: -0.8,
                      ),
                    ),
                    const SizedBox(height: 10),

                    // AI briefing — shimmer while loading, fade in when ready
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 500),
                      child: _briefingLoading
                          ? _BriefingShimmer(isDark: isDark)
                          : _BriefingText(
                              text: _briefing ?? '',
                              isDark: isDark,
                              tt: tt,
                            ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),

            // ── Daily Reset ─────────────────────────────────────
            _animated(
              1,
              ValueListenableBuilder<bool>(
                valueListenable: PremiumService.isPremium,
                builder: (context, isPremium, _) {
                  return GlassCard(
                    glowColor: AppColors.glowBlue,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SectionHeroCard(
                          title: 'Daily Reset',
                          subtitle:
                              'A quick moment to breathe and recenter',
                        ),
                        const SizedBox(height: 8),
                        SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: () =>
                                _openPremiumRoute('/reset'),
                            icon: Icon(isPremium
                                ? Icons.self_improvement_rounded
                                : Icons.lock_rounded),
                            label: Text(isPremium
                                ? 'Quick Reset'
                                : 'Unlock Daily Reset'),
                            style: FilledButton.styleFrom(
                              minimumSize: const Size.fromHeight(54),
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        Text(
                          '60 seconds to calm your mind.',
                          style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.55)
                                : Colors.black.withValues(alpha: 0.55),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            const SizedBox(height: 12),

            // ── Chat buttons ─────────────────────────────────────
            _animated(
              2,
              Row(
                children: [
                  Expanded(
                    child: GlassCard(
                      glowColor: AppColors.glowBlue,
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        children: [
                          Container(
                            width: 50,
                            height: 50,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Color(0xFF4D7CFF),
                                  Color(0xFF74C3FF)
                                ],
                              ),
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.primary
                                      .withValues(alpha: 0.35),
                                  blurRadius: 16,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            child: const Icon(Icons.chat_rounded,
                                color: Colors.white, size: 24),
                          ),
                          const SizedBox(height: 10),
                          Text('Text Chat',
                              style: tt.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w800)),
                          const SizedBox(height: 4),
                          Text('Type your thoughts',
                              style: tt.bodySmall?.copyWith(
                                color: cs.onSurface
                                    .withValues(alpha: 0.55),
                              ),
                              textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              onPressed: () => Navigator.of(context)
                                  .pushNamed('/chat'),
                              style: FilledButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 10),
                              ),
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
                            width: 50,
                            height: 50,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                                colors: [
                                  Color(0xFF32D0BE),
                                  Color(0xFF89E0CF)
                                ],
                              ),
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: AppColors.mintDeep
                                      .withValues(alpha: 0.35),
                                  blurRadius: 16,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            child: const Icon(Icons.mic_rounded,
                                color: Colors.white, size: 24),
                          ),
                          const SizedBox(height: 10),
                          Text('Voice Chat',
                              style: tt.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w800)),
                          const SizedBox(height: 4),
                          Text('Speak hands-free',
                              style: tt.bodySmall?.copyWith(
                                color: cs.onSurface
                                    .withValues(alpha: 0.55),
                              ),
                              textAlign: TextAlign.center),
                          const SizedBox(height: 12),
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              onPressed: () => Navigator.of(context)
                                  .pushNamed('/voice-chat'),
                              style: FilledButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                    vertical: 10),
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
              ),
            ),
            const SizedBox(height: 12),

            // ── Guided Sessions ─────────────────────────────────
            _animated(
              3,
              ValueListenableBuilder<bool>(
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
                            onPressed: () => _openPremiumRoute(
                                '/guided-sessions'),
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
              ),
            ),
            const SizedBox(height: 12),

            // ── Recommended for you ────────────────────────────
            if (_supportSuggestion != null)
              _animated(
                4,
                GlassCard(
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
                                crossAxisAlignment:
                                    CrossAxisAlignment.start,
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
                      Row(
                        children: [
                          Expanded(
                            child: FilledButton.icon(
                              onPressed: _openRecommendation,
                              icon: Icon(_supportSuggestion!.icon,
                                  size: 18),
                              label:
                                  Text(_supportSuggestion!.ctaLabel),
                            ),
                          ),
                          const SizedBox(width: 10),
                          TtsSpeakerButton(
                            text:
                                '${_supportSuggestion!.title}. ${_supportSuggestion!.subtitle}',
                            surface: TtsSurface.recommendation,
                            moodLabel: 'calm',
                            messageId:
                                'speak_recommendation_${_supportSuggestion!.id}',
                          ),
                          const SizedBox(width: 8),
                          const TtsReplayButton(
                              surface: TtsSurface.recommendation),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            if (_supportSuggestion != null) const SizedBox(height: 12),

            // ── Journal ──────────────────────────────────────────
            _animated(
              5,
              GlassCard(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeroCard(
                      title: 'Journal',
                      subtitle: 'You can write anything here.',
                    ),
                    const SizedBox(height: 12),
                    NestCard(
                      child: TextField(
                        controller: _plan,
                        maxLines: 4,
                        textInputAction: TextInputAction.newline,
                        decoration: const InputDecoration(
                          hintText: 'A few lines is enough…',
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
                                onPressed:
                                    _savingPlan ? null : _saveJournal,
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(
                                      vertical: 12.0),
                                  child: Text(_savingPlan
                                      ? 'Saving…'
                                      : 'Save entry'),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            OutlinedButton.icon(
                              onPressed: () =>
                                  _openPremiumRoute('/daily-hub'),
                              icon: Icon(
                                isPremium
                                    ? Icons.visibility_rounded
                                    : Icons.lock_rounded,
                                size: 16,
                              ),
                              label: const Padding(
                                padding: EdgeInsets.symmetric(
                                    vertical: 12.0),
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
            ),
          ],
        ),
      ),
    );
  }
}

// ── Briefing shimmer (loading state) ─────────────────────────────

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
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) {
        final alpha = 0.08 + _anim.value * 0.12;
        return Column(
          children: [
            Container(
              width: 240,
              height: 13,
              decoration: BoxDecoration(
                color: (widget.isDark ? Colors.white : Colors.black)
                    .withValues(alpha: alpha),
                borderRadius: BorderRadius.circular(6),
              ),
            ),
            const SizedBox(height: 6),
            Container(
              width: 180,
              height: 11,
              decoration: BoxDecoration(
                color: (widget.isDark ? Colors.white : Colors.black)
                    .withValues(alpha: alpha * 0.7),
                borderRadius: BorderRadius.circular(6),
              ),
            ),
          ],
        );
      },
    );
  }
}

// ── Briefing text (fade in) ──────────────────────────────────

class _BriefingText extends StatelessWidget {
  final String text;
  final bool isDark;
  final TextTheme tt;

  const _BriefingText({
    required this.text,
    required this.isDark,
    required this.tt,
  });

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
