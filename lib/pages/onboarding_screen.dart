// lib/pages/onboarding_screen.dart
//
// Cinematic first-launch onboarding — 5 stages:
//  Stage 0: Orb reveal + tagline
//  Stage 1: Mission statement (3 lines staggered)
//  Stage 2: Feature carousel (3 swipeable cards)
//  Stage 3: Disclaimer (must acknowledge)
//  Stage 4: Notification permission

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/mood_orb.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/settings_service.dart';

enum _Stage { orb, mission, features, disclaimer, notifications }

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onFinish;
  const OnboardingScreen({super.key, required this.onFinish});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>
    with TickerProviderStateMixin {
  _Stage _stage = _Stage.orb;

  late final AnimationController _orbCtrl;
  late final Animation<double> _orbFade;
  late final Animation<double> _taglineFade;
  late final Animation<Offset> _taglineSlide;

  late final AnimationController _missionCtrl;
  late final Animation<double> _l1Fade;
  late final Animation<double> _l2Fade;
  late final Animation<double> _l3Fade;
  late final Animation<Offset> _l1Slide;
  late final Animation<Offset> _l2Slide;
  late final Animation<Offset> _l3Slide;

  final PageController _pageCtrl = PageController();
  int _featureIndex = 0;
  bool _notifChosen = false;

  late final AnimationController _stageFadeCtrl;
  late final Animation<double> _stageFade;

  @override
  void initState() {
    super.initState();

    _orbCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 2200));
    _orbFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
          parent: _orbCtrl,
          curve: const Interval(0.0, 0.60, curve: Curves.easeOut)),
    );
    _taglineFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
          parent: _orbCtrl,
          curve: const Interval(0.55, 1.0, curve: Curves.easeOut)),
    );
    _taglineSlide =
        Tween<Offset>(begin: const Offset(0, 0.08), end: Offset.zero).animate(
      CurvedAnimation(
          parent: _orbCtrl,
          curve: const Interval(0.55, 1.0, curve: Curves.easeOut)),
    );

    _missionCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1800));

    Interval iv(double s, double e) => Interval(s, e, curve: Curves.easeOut);
    Tween<Offset> st() =>
        Tween<Offset>(begin: const Offset(0, 0.10), end: Offset.zero);

    _l1Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.0, 0.40)));
    _l2Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.28, 0.65)));
    _l3Fade = Tween<double>(begin: 0.0, end: 1.0)
        .animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.55, 0.90)));
    _l1Slide = st().animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.0, 0.40)));
    _l2Slide = st().animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.28, 0.65)));
    _l3Slide = st().animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.55, 0.90)));

    _stageFadeCtrl = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 400),
        value: 1.0);
    _stageFade =
        CurvedAnimation(parent: _stageFadeCtrl, curve: Curves.easeInOut);

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
              curve: Curves.easeOutCubic);
        } else {
          await _goToStage(_Stage.disclaimer);
        }
        break;
      case _Stage.disclaimer:
        await _goToStage(_Stage.notifications);
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

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: FadeTransition(
          opacity: _stageFade,
          child: SafeArea(child: _buildStage(tt, isDark)),
        ),
      ),
    );
  }

  Widget _buildStage(TextTheme tt, bool isDark) {
    switch (_stage) {
      case _Stage.orb:           return _buildOrbStage(tt, isDark);
      case _Stage.mission:       return _buildMissionStage(tt, isDark);
      case _Stage.features:      return _buildFeaturesStage(tt, isDark);
      case _Stage.disclaimer:    return _buildDisclaimerStage(tt, isDark);
      case _Stage.notifications: return _buildNotificationsStage(tt, isDark);
    }
  }

  // ── Stage 0 ────────────────────────────────────────────────────────────
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
            AnimatedBuilder(
              animation: _orbFade,
              builder: (_, child) =>
                  Opacity(opacity: _orbFade.value, child: child),
              child: const MoodOrb(size: 200),
            ),
            const SizedBox(height: 40),
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
                      color:
                          isDark ? Colors.white : const Color(0xFF0E1320),
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

  // ── Stage 1 ────────────────────────────────────────────────────────────
  Widget _buildMissionStage(TextTheme tt, bool isDark) {
    final textColor   = isDark ? Colors.white : const Color(0xFF0E1320);
    final subtleColor = isDark
        ? Colors.white.withValues(alpha: 0.60)
        : const Color(0xFF475467);

    Widget stLine(Animation<double> fade, Animation<Offset> slide,
        String text, TextStyle? style) {
      return AnimatedBuilder(
        animation: fade,
        builder: (_, child) => Opacity(
            opacity: fade.value,
            child: SlideTransition(position: slide, child: child)),
        child: Text(text, textAlign: TextAlign.center, style: style),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 2),
          stLine(_l1Fade, _l1Slide,
              'MindCore AI was built for the moments\nwhen everything feels like too much.',
              tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: textColor,
                  letterSpacing: -0.6,
                  height: 1.25)),
          const SizedBox(height: 24),
          stLine(_l2Fade, _l2Slide,
              'Not to fix you.\nJust to be there with you.',
              tt.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: subtleColor,
                  height: 1.4)),
          const SizedBox(height: 24),
          stLine(_l3Fade, _l3Slide, 'Calm. Private. Always ready.',
              tt.bodyLarge?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : const Color(0xFF94A3B8),
                  letterSpacing: 0.3)),
          const Spacer(flex: 2),
          _BottomButton(
              label: 'Continue',
              onTap: _handleContinue,
              color: AppColors.primary),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  // ── Stage 2 ────────────────────────────────────────────────────────────
  static const _features = [
    _FeatureData(
        icon: Icons.psychology_rounded,
        color: Color(0xFF4D7CFF),
        title: 'AI that actually listens',
        body:
            "Not scripted responses. MindCore reads your mood, your history, and how you're feeling right now — and responds accordingly."),
    _FeatureData(
        icon: Icons.self_improvement_rounded,
        color: Color(0xFF32D0BE),
        title: 'Tools that work in real time',
        body:
            'Guided breathing, voice chat, grounding audio, and a daily reset — all available in one tap, whenever you need them.'),
    _FeatureData(
        icon: Icons.insights_rounded,
        color: Color(0xFF9B7FFF),
        title: 'Patterns that help you understand yourself',
        body:
            'Weekly mood reports, streak tracking, and pattern detection — so you start to see what helps and what to watch.'),
  ];

  Widget _buildFeaturesStage(TextTheme tt, bool isDark) {
    final isLast = _featureIndex == 2;
    return Column(
      children: [
        const SizedBox(height: 24),
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
                            width: 72, height: 72,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: f.color.withValues(alpha: 0.15),
                              border: Border.all(
                                  color: f.color.withValues(alpha: 0.35),
                                  width: 1.5),
                            ),
                            child: Icon(f.icon, color: f.color, size: 34),
                          ),
                          const SizedBox(height: 22),
                          Text(f.title,
                              textAlign: TextAlign.center,
                              style: tt.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  color: isDark
                                      ? Colors.white
                                      : const Color(0xFF0E1320),
                                  letterSpacing: -0.5)),
                          const SizedBox(height: 14),
                          Text(f.body,
                              textAlign: TextAlign.center,
                              style: tt.bodyMedium?.copyWith(
                                  color: isDark
                                      ? Colors.white.withValues(alpha: 0.60)
                                      : const Color(0xFF475467),
                                  height: 1.55)),
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
            label: isLast ? 'Almost there →' : 'Next',
            onTap: _handleContinue,
            color: _features[_featureIndex].color,
          ),
        ),
      ],
    );
  }

  // ── Stage 3: Disclaimer ───────────────────────────────────────────
  Widget _buildDisclaimerStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 24),

          // Icon
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFFFF6B6B).withValues(alpha: 0.12),
              border: Border.all(
                  color: const Color(0xFFFF6B6B).withValues(alpha: 0.35),
                  width: 1.5),
            ),
            child: const Icon(Icons.info_outline_rounded,
                color: Color(0xFFFF6B6B), size: 30),
          ),
          const SizedBox(height: 16),

          Text(
            'Before you begin',
            textAlign: TextAlign.center,
            style: tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: 20),

          // Disclaimer content
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  GlassCard(
                    glowColor: const Color(0x44FF6B6B),
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _DisclaimerRow(
                          icon: Icons.smart_toy_rounded,
                          color: AppColors.primary,
                          title: 'Not a medical service',
                          body:
                              'MindCore AI is a personal wellness companion, not a licensed therapy or medical platform.',
                          tt: tt,
                          isDark: isDark,
                        ),
                        const SizedBox(height: 14),
                        _DisclaimerRow(
                          icon: Icons.person_rounded,
                          color: AppColors.mintDeep,
                          title: 'Not a replacement for professional help',
                          body:
                              'AI responses are not a substitute for advice from a qualified mental health professional. Please seek professional support when needed.',
                          tt: tt,
                          isDark: isDark,
                        ),
                        const SizedBox(height: 14),
                        _DisclaimerRow(
                          icon: Icons.warning_amber_rounded,
                          color: const Color(0xFFFF6B6B),
                          title: 'In a crisis or emergency',
                          body:
                              'If you are in immediate danger or experiencing a mental health emergency, please contact your local emergency services or a crisis helpline.',
                          tt: tt,
                          isDark: isDark,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),

                  // Crisis numbers strip
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF6B6B).withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: const Color(0xFFFF6B6B)
                              .withValues(alpha: 0.25)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Crisis helplines',
                            style: tt.labelSmall?.copyWith(
                                color: const Color(0xFFFF6B6B),
                                fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Text(
                          '• Malta: 1579\n'
                          '• USA/Canada: 988\n'
                          '• UK & Ireland: 116 123 (Samaritans)\n'
                          '• Australia: 13 11 14 (Lifeline)\n'
                          '• International: findahelpline.com',
                          style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.65)
                                : const Color(0xFF475467),
                            height: 1.7,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Acknowledge button
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _handleContinue,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                minimumSize: const Size.fromHeight(54),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16)),
              ),
              child: const Text(
                'I understand — Continue',
                style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    fontSize: 15),
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Stage 4: Notifications ──────────────────────────────────────────
  Widget _buildNotificationsStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          Container(
            width: 80, height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primary.withValues(alpha: 0.12),
              border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.30),
                  width: 1.5),
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
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: () => _handleNotification(true),
                style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(54),
                    backgroundColor: AppColors.primary),
                icon: const Icon(Icons.notifications_active_rounded,
                    color: Colors.white),
                label: const Text('Yes, remind me daily'),
              ),
            ),
            const SizedBox(height: 12),
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

// ── Helpers ───────────────────────────────────────────────────────────────────

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

class _DisclaimerRow extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final TextTheme tt;
  final bool isDark;
  const _DisclaimerRow(
      {required this.icon,
      required this.color,
      required this.title,
      required this.body,
      required this.tt,
      required this.isDark});
  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 34, height: 34,
          decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withValues(alpha: 0.12)),
          child: Icon(icon, color: color, size: 17),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: tt.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: isDark
                          ? Colors.white
                          : const Color(0xFF0E1320))),
              const SizedBox(height: 4),
              Text(body,
                  style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.60)
                          : const Color(0xFF475467),
                      height: 1.5)),
            ],
          ),
        ),
      ],
    );
  }
}

class _FeatureData {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  const _FeatureData(
      {required this.icon,
      required this.color,
      required this.title,
      required this.body});
}
