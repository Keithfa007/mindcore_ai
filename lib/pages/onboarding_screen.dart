// lib/pages/onboarding_screen.dart
//
// Cinematic first-launch onboarding — 4 stages:
//  Stage 0: Orb reveal + tagline
//  Stage 1: Mission statement (3 lines staggered)
//  Stage 2: Feature carousel (3 swipeable cards)
//  Stage 3: Notification permission
//
// The gate (PostLoginGate) handles the onboarding_done_v1 flag.
// This screen just calls onFinish() when done.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/mood_orb.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/settings_service.dart';

enum _Stage { orb, mission, features, notifications }

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onFinish;
  const OnboardingScreen({super.key, required this.onFinish});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>
    with TickerProviderStateMixin {
  _Stage _stage = _Stage.orb;

  // ── Stage 0: orb + tagline ────────────────────────────────────────────
  late final AnimationController _orbCtrl;
  late final Animation<double> _orbFade;
  late final Animation<double> _taglineFade;
  late final Animation<Offset> _taglineSlide;

  // ── Stage 1: mission lines ────────────────────────────────────────────
  late final AnimationController _missionCtrl;
  late final Animation<double> _l1Fade;
  late final Animation<double> _l2Fade;
  late final Animation<double> _l3Fade;
  late final Animation<Offset> _l1Slide;
  late final Animation<Offset> _l2Slide;
  late final Animation<Offset> _l3Slide;

  // ── Stage 2: feature carousel ─────────────────────────────────────────
  final PageController _pageCtrl = PageController();
  int _featureIndex = 0;

  // ── Stage 3: notification choice made ────────────────────────────────
  bool _notifChosen = false;

  // ── Global fade between stages ────────────────────────────────────────
  late final AnimationController _stageFadeCtrl;
  late final Animation<double> _stageFade;

  @override
  void initState() {
    super.initState();

    // Orb reveal: orb fades in 0–60%, tagline fades in 55–100%
    _orbCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2200),
    );
    _orbFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _orbCtrl,
        curve: const Interval(0.0, 0.60, curve: Curves.easeOut),
      ),
    );
    _taglineFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _orbCtrl,
        curve: const Interval(0.55, 1.0, curve: Curves.easeOut),
      ),
    );
    _taglineSlide = Tween<Offset>(
      begin: const Offset(0, 0.08),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _orbCtrl,
        curve: const Interval(0.55, 1.0, curve: Curves.easeOut),
      ),
    );

    // Mission: 3 lines stagger in over 1800ms
    _missionCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );

    Interval _iv(double s, double e) =>
        Interval(s, e, curve: Curves.easeOut);

    _l1Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.0, 0.40)));
    _l2Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.28, 0.65)));
    _l3Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.55, 0.90)));

    Tween<Offset> _slideTween() =>
        Tween<Offset>(begin: const Offset(0, 0.10), end: Offset.zero);

    _l1Slide = _slideTween()
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.0, 0.40)));
    _l2Slide = _slideTween()
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.28, 0.65)));
    _l3Slide = _slideTween()
        .animate(CurvedAnimation(parent: _missionCtrl, curve: _iv(0.55, 0.90)));

    // Global stage fade
    _stageFadeCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
      value: 1.0,
    );
    _stageFade = CurvedAnimation(parent: _stageFadeCtrl, curve: Curves.easeInOut);

    // Start orb reveal immediately
    _orbCtrl.forward();
  }

  @override
  void dispose() {
    _orbCtrl.dispose();
    _missionCtrl.dispose();
    _stageFadeCtrl.dispose();
    _pageCtrl.dispose();
    super.dispose();
  }

  // ── Stage transitions ─────────────────────────────────────────────────

  Future<void> _goToStage(_Stage next) async {
    HapticFeedback.selectionClick();
    await _stageFadeCtrl.reverse();
    if (!mounted) return;
    setState(() => _stage = next);
    if (next == _Stage.mission) _missionCtrl.forward(from: 0);
    await _stageFadeCtrl.forward();
  }

  Future<void> _handleContinue() async {
    switch (_stage) {
      case _Stage.orb:
        await _goToStage(_Stage.mission);
        break;
      case _Stage.mission:
        await _goToStage(_Stage.features);
        break;
      case _Stage.features:
        if (_featureIndex < 2) {
          _pageCtrl.nextPage(
            duration: const Duration(milliseconds: 320),
            curve: Curves.easeOutCubic,
          );
        } else {
          await _goToStage(_Stage.notifications);
        }
        break;
      case _Stage.notifications:
        widget.onFinish();
        break;
    }
  }

  Future<void> _handleNotification(bool enable) async {
    await SettingsService.setDailyReminderEnabled(enable);
    HapticFeedback.lightImpact();
    setState(() => _notifChosen = true);
    await Future.delayed(const Duration(milliseconds: 600));
    if (!mounted) return;
    widget.onFinish();
  }

  // ── Build ─────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: FadeTransition(
          opacity: _stageFade,
          child: SafeArea(
            child: _buildStage(tt, isDark),
          ),
        ),
      ),
    );
  }

  Widget _buildStage(TextTheme tt, bool isDark) {
    switch (_stage) {
      case _Stage.orb:
        return _buildOrbStage(tt, isDark);
      case _Stage.mission:
        return _buildMissionStage(tt, isDark);
      case _Stage.features:
        return _buildFeaturesStage(tt, isDark);
      case _Stage.notifications:
        return _buildNotificationsStage(tt, isDark);
    }
  }

  // ── Stage 0: Orb reveal ───────────────────────────────────────────────

  Widget _buildOrbStage(TextTheme tt, bool isDark) {
    return GestureDetector(
      onTap: _handleContinue,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Spacer(flex: 2),

            // Orb fades in
            AnimatedBuilder(
              animation: _orbFade,
              builder: (_, child) => Opacity(opacity: _orbFade.value, child: child),
              child: const MoodOrb(size: 200),
            ),

            const SizedBox(height: 40),

            // Tagline fades + slides in
            AnimatedBuilder(
              animation: _taglineFade,
              builder: (_, child) => Opacity(
                opacity: _taglineFade.value,
                child: SlideTransition(position: _taglineSlide, child: child),
              ),
              child: Column(
                children: [
                  Text(
                    'You deserve to feel better.',
                    textAlign: TextAlign.center,
                    style: tt.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: isDark ? Colors.white : const Color(0xFF0E1320),
                      letterSpacing: -0.8,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'A calm, private space — always in your pocket.',
                    textAlign: TextAlign.center,
                    style: tt.bodyMedium?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.55)
                          : const Color(0xFF475467),
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),

            const Spacer(flex: 2),

            // Tap hint
            AnimatedBuilder(
              animation: _taglineFade,
              builder: (_, child) =>
                  Opacity(opacity: _taglineFade.value, child: child),
              child: Text(
                'Tap anywhere to continue',
                style: tt.labelSmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.30)
                      : Colors.black.withValues(alpha: 0.30),
                  letterSpacing: 0.5,
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  // ── Stage 1: Mission ──────────────────────────────────────────────────

  Widget _buildMissionStage(TextTheme tt, bool isDark) {
    final textColor =
        isDark ? Colors.white : const Color(0xFF0E1320);
    final subtleColor = isDark
        ? Colors.white.withValues(alpha: 0.60)
        : const Color(0xFF475467);

    Widget _staggeredLine(
      Animation<double> fade,
      Animation<Offset> slide,
      String text,
      TextStyle? style,
    ) {
      return AnimatedBuilder(
        animation: fade,
        builder: (_, child) => Opacity(
          opacity: fade.value,
          child: SlideTransition(position: slide, child: child),
        ),
        child: Text(text, textAlign: TextAlign.center, style: style),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 2),

          _staggeredLine(
            _l1Fade, _l1Slide,
            'MindCore AI was built for the moments\nwhen everything feels like too much.',
            tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: textColor,
              letterSpacing: -0.6,
              height: 1.25,
            ),
          ),
          const SizedBox(height: 24),

          _staggeredLine(
            _l2Fade, _l2Slide,
            'Not to fix you.\nJust to be there with you.',
            tt.titleLarge?.copyWith(
              fontWeight: FontWeight.w700,
              color: subtleColor,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 24),

          _staggeredLine(
            _l3Fade, _l3Slide,
            'Calm. Private. Always ready.',
            tt.bodyLarge?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : const Color(0xFF94A3B8),
              letterSpacing: 0.3,
            ),
          ),

          const Spacer(flex: 2),

          _BottomButton(
            label: 'Continue',
            onTap: _handleContinue,
            color: AppColors.primary,
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  // ── Stage 2: Feature carousel ─────────────────────────────────────────

  static const _features = [
    _FeatureData(
      icon: Icons.psychology_rounded,
      color: Color(0xFF4D7CFF),
      title: 'AI that actually listens',
      body:
          'Not scripted responses. MindCore reads your mood, your history, and how you\'re feeling right now — and responds accordingly.',
    ),
    _FeatureData(
      icon: Icons.self_improvement_rounded,
      color: Color(0xFF32D0BE),
      title: 'Tools that work in real time',
      body:
          'Guided breathing, voice chat, grounding audio, and a daily reset — all available in one tap, whenever you need them.',
    ),
    _FeatureData(
      icon: Icons.insights_rounded,
      color: Color(0xFF9B7FFF),
      title: 'Patterns that help you understand yourself',
      body:
          'Weekly mood reports, streak tracking, and pattern detection — so you start to see what helps and what to watch.',
    ),
  ];

  Widget _buildFeaturesStage(TextTheme tt, bool isDark) {
    final isLast = _featureIndex == 2;

    return Column(
      children: [
        const SizedBox(height: 24),

        // Dot indicator
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: List.generate(3, (i) {
            final active = i == _featureIndex;
            return AnimatedContainer(
              duration: const Duration(milliseconds: 250),
              margin: const EdgeInsets.symmetric(horizontal: 4),
              height: 6,
              width: active ? 22 : 6,
              decoration: BoxDecoration(
                color: active
                    ? _features[_featureIndex].color
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.20)
                        : Colors.black.withValues(alpha: 0.15)),
                borderRadius: BorderRadius.circular(3),
              ),
            );
          }),
        ),
        const SizedBox(height: 20),

        // Cards
        Expanded(
          child: PageView.builder(
            controller: _pageCtrl,
            itemCount: 3,
            onPageChanged: (i) => setState(() => _featureIndex = i),
            itemBuilder: (_, i) {
              final f = _features[i];
              return Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    GlassCard(
                      glowColor: f.color.withValues(alpha: 0.40),
                      padding: const EdgeInsets.all(28),
                      child: Column(
                        children: [
                          Container(
                            width: 72,
                            height: 72,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: f.color.withValues(alpha: 0.15),
                              border: Border.all(
                                color: f.color.withValues(alpha: 0.35),
                                width: 1.5,
                              ),
                            ),
                            child: Icon(f.icon, color: f.color, size: 34),
                          ),
                          const SizedBox(height: 22),
                          Text(
                            f.title,
                            textAlign: TextAlign.center,
                            style: tt.titleLarge?.copyWith(
                              fontWeight: FontWeight.w900,
                              color: isDark ? Colors.white : const Color(0xFF0E1320),
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 14),
                          Text(
                            f.body,
                            textAlign: TextAlign.center,
                            style: tt.bodyMedium?.copyWith(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.60)
                                  : const Color(0xFF475467),
                              height: 1.55,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),

        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
          child: _BottomButton(
            label: isLast ? 'Almost there \u2192' : 'Next',
            onTap: _handleContinue,
            color: _features[_featureIndex].color,
          ),
        ),
      ],
    );
  }

  // ── Stage 3: Notification permission ─────────────────────────────────

  Widget _buildNotificationsStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),

          // Icon
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withValues(alpha: 0.12),
              border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.30), width: 1.5),
            ),
            child: Icon(Icons.notifications_rounded,
                color: AppColors.primary, size: 38),
          ),
          const SizedBox(height: 28),

          Text(
            'Stay connected to yourself',
            textAlign: TextAlign.center,
            style: tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            'Would you like a gentle daily reminder to check in? Just once a day, at a time that suits you.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.60)
                  : const Color(0xFF475467),
              height: 1.55,
            ),
          ),

          const Spacer(),

          if (_notifChosen)
            Padding(
              padding: const EdgeInsets.only(bottom: 32),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle_rounded,
                      color: AppColors.mintDeep, size: 22),
                  const SizedBox(width: 8),
                  Text('Saved — taking you in…',
                      style: tt.bodyMedium?.copyWith(
                          color: AppColors.mintDeep,
                          fontWeight: FontWeight.w700)),
                ],
              ),
            )
          else ...[
            // Yes button
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _handleNotification(true),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                  backgroundColor: AppColors.primary,
                ),
                icon: const Icon(Icons.notifications_active_rounded,
                    color: Colors.white),
                label: const Text('Yes, remind me daily'),
              ),
            ),
            const SizedBox(height: 12),

            // No button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton(
                onPressed: () => _handleNotification(false),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(54),
                  side: BorderSide(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.20)
                        : Colors.black.withValues(alpha: 0.15),
                  ),
                ),
                child: Text(
                  'Not right now',
                  style: TextStyle(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.55)
                        : const Color(0xFF64748B),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ],
      ),
    );
  }
}

// ── Shared bottom button ──────────────────────────────────────────────────

class _BottomButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final Color color;
  const _BottomButton(
      {required this.label, required this.onTap, required this.color});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          backgroundColor: color,
          minimumSize: const Size.fromHeight(54),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16)),
        ),
        child: Text(label,
            style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 15)),
      ),
    );
  }
}

// ── Feature card data ─────────────────────────────────────────────────────

class _FeatureData {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  const _FeatureData({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
  });
}
