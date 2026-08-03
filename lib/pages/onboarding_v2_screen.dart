// lib/pages/onboarding_v2_screen.dart
//
// New value-first onboarding. Flow:
//   welcome -> safety & privacy consent -> 2 quick questions ->
//   LIVE personalised AI reply (the "taste") -> what's inside -> trust/founder
//   -> onFinish(). The notification opt-in is no longer here; it runs after the
//   user has an account and access (see NotificationOptInScreen).
//
// It is a drop-in replacement for OnboardingScreen: same `onFinish` contract,
// so post_login_gate can use it interchangeably. Consent copy and visual style
// are reused from the original onboarding so nothing looks off-brand and no
// legal/safety step is dropped.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/onboarding_taste_service.dart';

class OnboardingV2Screen extends StatefulWidget {
  final VoidCallback onFinish;
  const OnboardingV2Screen({super.key, required this.onFinish});

  @override
  State<OnboardingV2Screen> createState() => _OnboardingV2ScreenState();
}

class _OnboardingV2ScreenState extends State<OnboardingV2Screen>
    with TickerProviderStateMixin {
  static const int _stepCount = 7;
  int _step = 0;

  // Q1 (multi-select) + Q2 (single-select)
  final Set<String> _feelings = {};
  String? _timing;

  // Taste state
  bool _tasteStarted = false;
  bool _tasteDone = false;
  String _tasteText = '';

  late final AnimationController _fadeCtrl;
  late final Animation<double> _fade;

  // ── Data ───────────────────────────────────────────────────────────────────

  static const List<List<String>> _feelingOptions = [
    ['🌧️', 'Loneliness'],
    ['💭', 'Anxiety'],
    ['🔥', 'Stress'],
    ['🌙', 'Sleep'],
    ['🕳️', 'Low mood'],
    ['🌱', 'Recovery'],
    ['🔁', 'Overthinking'],
    ['🤍', 'Grief'],
  ];

  static const List<List<String>> _timingOptions = [
    ['🌙', 'Late at night', 'late at night'],
    ['🌅', 'Early mornings', 'first thing in the morning'],
    ['☀️', 'Middle of the day', 'in the middle of the day'],
    ['🌊', 'It comes and goes', 'when I least expect it'],
  ];

  static const List<List<String>> _features = [
    ['💬', 'Talk anytime', '7 caring modes for whatever you need'],
    ['🎙️', 'Voice chats', 'Speak out loud, hear a warm reply'],
    ['🌱', 'Mood tracking', 'See your patterns, gently'],
    ['🫁', 'Calm sessions', 'Breathing and guided relief'],
    ['🆘', 'SOS mode', 'For the hardest moments'],
    ['📓', 'Private journal', 'Yours alone, with AI insight'],
  ];

  @override
  void initState() {
    super.initState();
    _fadeCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 380), value: 1.0);
    _fade = CurvedAnimation(parent: _fadeCtrl, curve: Curves.easeInOut);
  }

  @override
  void dispose() {
    _fadeCtrl.dispose();
    super.dispose();
  }

  // ── Navigation ──────────────────────────────────────────────────────────────

  Future<void> _go(int next) async {
    if (next < 0 || next >= _stepCount) return;
    HapticFeedback.selectionClick();
    await _fadeCtrl.reverse();
    if (!mounted) return;
    setState(() => _step = next);
    await _fadeCtrl.forward();
    if (next == 4) _startTaste();
  }

  Future<void> _startTaste() async {
    if (_tasteStarted) return;
    _tasteStarted = true;

    final feeling =
        _feelings.isNotEmpty ? _feelings.first.toLowerCase() : "what's on my mind";
    final timing = _timing ?? 'late at night';

    await OnboardingTasteService.streamTaste(
      feeling: feeling,
      timing: timing,
      onDelta: (delta) async {
        if (!mounted) return;
        setState(() => _tasteText += delta);
      },
    );
    if (!mounted) return;
    setState(() => _tasteDone = true);
  }

  // ── Build ───────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final showBack = _step > 0 && _step < _stepCount - 1 && _step != 4;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Column(
            children: [
              // Progress + back
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 6),
                child: Row(
                  children: [
                    SizedBox(
                      width: 32,
                      child: showBack
                          ? _RoundIcon(
                              icon: Icons.arrow_back_ios_new_rounded,
                              isDark: isDark,
                              onTap: () => _go(_step - 1),
                            )
                          : const SizedBox.shrink(),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(99),
                        child: LinearProgressIndicator(
                          value: (_step + 1) / _stepCount,
                          minHeight: 4,
                          backgroundColor: isDark
                              ? Colors.white.withValues(alpha: 0.10)
                              : Colors.black.withValues(alpha: 0.08),
                          valueColor:
                              AlwaysStoppedAnimation<Color>(AppColors.primary),
                        ),
                      ),
                    ),
                    const SizedBox(width: 40),
                  ],
                ),
              ),
              Expanded(
                child: FadeTransition(
                  opacity: _fade,
                  child: _buildStep(tt, isDark),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStep(TextTheme tt, bool isDark) {
    switch (_step) {
      case 0:
        return _welcome(tt, isDark);
      case 1:
        return _consent(tt, isDark);
      case 2:
        return _question1(tt, isDark);
      case 3:
        return _question2(tt, isDark);
      case 4:
        return _taste(tt, isDark);
      case 5:
        return _whatsInside(tt, isDark);
      case 6:
        return _trust(tt, isDark);
      default:
        return const SizedBox.shrink();
    }
  }

  // ── Step 0: Welcome ─────────────────────────────────────────────────────────

  Widget _welcome(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Spacer(flex: 3),
          _eyebrow('DONE SUFFERING IN SILENCE'),
          const SizedBox(height: 14),
          Text(
            "You don't have to\ndo this alone.",
            style: tt.headlineMedium?.copyWith(
              fontWeight: FontWeight.w900,
              height: 1.15,
              letterSpacing: -0.6,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'A private space to talk, and feel a little lighter. '
            'Any hour of the day or night, someone is here.',
            style: tt.bodyLarge?.copyWith(
              height: 1.5,
              color: _subtle(isDark),
            ),
          ),
          const Spacer(flex: 4),
          _PrimaryButton(label: 'Get started', onTap: () => _go(1)),
          const SizedBox(height: 12),
          Center(
            child: Text('Takes about a minute. No pressure.',
                style: tt.bodySmall?.copyWith(color: _subtle(isDark))),
          ),
          const SizedBox(height: 28),
        ],
      ),
    );
  }

  // ── Step 1: Safety & privacy consent (combined) ─────────────────────────────

  Widget _consent(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 12),
          Text('Before we begin',
              textAlign: TextAlign.center,
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.6,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 6),
          Text('A quick word on safety and your privacy.',
              textAlign: TextAlign.center,
              style: tt.bodyMedium?.copyWith(color: _subtle(isDark), height: 1.5)),
          const SizedBox(height: 18),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  GlassCard(
                    glowColor: const Color(0x44FF6B6B),
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _InfoRow(
                          icon: Icons.favorite_rounded,
                          color: const Color(0xFFFF6B6B),
                          title: 'A companion, not medical care',
                          body:
                              'MindCore is a personal wellness companion, not therapy or a medical service, and not a replacement for professional help.',
                          tt: tt,
                          isDark: isDark,
                        ),
                        const SizedBox(height: 14),
                        _InfoRow(
                          icon: Icons.health_and_safety_rounded,
                          color: const Color(0xFFFF6B6B),
                          title: 'In a crisis',
                          body:
                              'If you are in immediate danger, contact your local emergency services or a helpline. Malta 1579, UK & Ireland 116 123, USA/Canada 988, Australia 13 11 14, or findahelpline.com.',
                          tt: tt,
                          isDark: isDark,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  GlassCard(
                    glowColor: AppColors.primary.withValues(alpha: 0.15),
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _InfoRow(
                          icon: Icons.lock_rounded,
                          color: AppColors.primary,
                          title: 'Private by design',
                          body:
                              'Your conversations stay yours. No ads, no data selling, and your words are never used to train any AI.',
                          tt: tt,
                          isDark: isDark,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(label: 'I understand, continue', onTap: () => _go(2)),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Step 2: Question 1 (feelings, multi-select) ─────────────────────────────

  Widget _question1(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          _eyebrow('A FEW QUICK THINGS'),
          const SizedBox(height: 10),
          Text("What's weighing on you\nmost right now?",
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  height: 1.2,
                  letterSpacing: -0.4,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 8),
          Text('Pick anything that fits. It shapes how MindCore talks with you.',
              style: tt.bodyMedium?.copyWith(color: _subtle(isDark), height: 1.5)),
          const SizedBox(height: 22),
          Expanded(
            child: SingleChildScrollView(
              child: Wrap(
                spacing: 10,
                runSpacing: 10,
                children: _feelingOptions.map((f) {
                  final label = f[1];
                  final selected = _feelings.contains(label);
                  return _Pill(
                    emoji: f[0],
                    label: label,
                    selected: selected,
                    isDark: isDark,
                    tt: tt,
                    onTap: () {
                      HapticFeedback.selectionClick();
                      setState(() {
                        if (selected) {
                          _feelings.remove(label);
                        } else {
                          _feelings.add(label);
                        }
                      });
                    },
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(
            label: 'Continue',
            enabled: _feelings.isNotEmpty,
            onTap: () => _go(3),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Step 3: Question 2 (timing, single-select) ──────────────────────────────

  Widget _question2(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          _eyebrow('ONE MORE'),
          const SizedBox(height: 10),
          Text('When does it hit\nthe hardest?',
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  height: 1.2,
                  letterSpacing: -0.4,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 8),
          Text('The quiet hours are often the loudest. We will be ready then.',
              style: tt.bodyMedium?.copyWith(color: _subtle(isDark), height: 1.5)),
          const SizedBox(height: 22),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: _timingOptions.map((t) {
                  final label = t[1];
                  final value = t[2];
                  final selected = _timing == value;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 11),
                    child: _OptionRow(
                      emoji: t[0],
                      label: label,
                      selected: selected,
                      isDark: isDark,
                      tt: tt,
                      onTap: () {
                        HapticFeedback.selectionClick();
                        setState(() => _timing = value);
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(
            label: 'Continue',
            enabled: _timing != null,
            onTap: () => _go(4),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Step 4: Live AI taste ───────────────────────────────────────────────────

  Widget _taste(TextTheme tt, bool isDark) {
    final feeling =
        _feelings.isNotEmpty ? _feelings.first.toLowerCase() : "what's on my mind";
    final timing = _timing ?? 'late at night';
    final userMsg =
        "I've been dealing with $feeling, mostly ${_shortTiming(timing)}.";

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          _eyebrow('YOUR COMPANION'),
          const SizedBox(height: 8),
          Text('Someone who actually\nlistens.',
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  height: 1.2,
                  letterSpacing: -0.4,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 18),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // user bubble
                  Align(
                    alignment: Alignment.centerRight,
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 260),
                      padding:
                          const EdgeInsets.symmetric(horizontal: 15, vertical: 11),
                      decoration: BoxDecoration(
                        color: AppColors.primary,
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(18),
                          topRight: Radius.circular(18),
                          bottomLeft: Radius.circular(18),
                          bottomRight: Radius.circular(5),
                        ),
                      ),
                      child: Text(userMsg,
                          style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                              height: 1.4)),
                    ),
                  ),
                  const SizedBox(height: 12),
                  // AI bubble
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      constraints: const BoxConstraints(maxWidth: 300),
                      padding: const EdgeInsets.all(15),
                      decoration: BoxDecoration(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.07)
                            : Colors.black.withValues(alpha: 0.04),
                        border: Border.all(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.12)
                                : Colors.black.withValues(alpha: 0.08)),
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(18),
                          topRight: Radius.circular(18),
                          bottomLeft: Radius.circular(5),
                          bottomRight: Radius.circular(18),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('COMPANION',
                              style: tt.labelSmall?.copyWith(
                                  color: AppColors.mintDeep,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.5)),
                          const SizedBox(height: 6),
                          _tasteText.isEmpty
                              ? const _TypingDots()
                              : Text(_tasteText,
                                  style: tt.bodyMedium?.copyWith(
                                      height: 1.5,
                                      color: isDark
                                          ? Colors.white.withValues(alpha: 0.92)
                                          : const Color(0xFF0E1320))),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(
            label: 'I want more of this',
            enabled: _tasteDone,
            onTap: () => _go(5),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Step 5: What's inside ───────────────────────────────────────────────────

  Widget _whatsInside(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          _eyebrow("WHAT'S INSIDE"),
          const SizedBox(height: 8),
          Text('Everything, in one\ncalm place.',
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  height: 1.2,
                  letterSpacing: -0.4,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 20),
          Expanded(
            child: SingleChildScrollView(
              child: GridView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _features.length,
                gridDelegate:
                    const SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  mainAxisSpacing: 11,
                  crossAxisSpacing: 11,
                  mainAxisExtent: 150,
                ),
                itemBuilder: (context, i) {
                  final f = _features[i];
                  return GlassCard(
                    glowColor: AppColors.primary.withValues(alpha: 0.10),
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(f[0], style: const TextStyle(fontSize: 24)),
                        const SizedBox(height: 8),
                        Text(f[1],
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: tt.titleSmall?.copyWith(
                                fontWeight: FontWeight.w800,
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF0E1320))),
                        const SizedBox(height: 3),
                        Text(f[2],
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: tt.bodySmall?.copyWith(
                                height: 1.3, color: _subtle(isDark))),
                      ],
                    ),
                  );
                },
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(label: 'Continue', onTap: () => _go(6)),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Step 6: Trust / founder ─────────────────────────────────────────────────

  Widget _trust(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 8),
          _eyebrow('WHY PEOPLE STAY'),
          const SizedBox(height: 8),
          Text("You're not alone in this.",
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  height: 1.2,
                  letterSpacing: -0.4,
                  color: isDark ? Colors.white : const Color(0xFF0E1320))),
          const SizedBox(height: 20),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  // Founder card
                  GlassCard(
                    glowColor: AppColors.mintDeep.withValues(alpha: 0.18),
                    padding: const EdgeInsets.all(18),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 44,
                          height: 44,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppColors.mintDeep.withValues(alpha: 0.18),
                          ),
                          child: Text('K',
                              style: tt.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  color: AppColors.mintDeep)),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('Built by someone who has been there',
                                  style: tt.titleSmall?.copyWith(
                                      fontWeight: FontWeight.w800,
                                      color: isDark
                                          ? Colors.white
                                          : const Color(0xFF0E1320))),
                              const SizedBox(height: 6),
                              Text(
                                'For over twenty years I worked nights in an industry that '
                                'never sleeps, and for a lot of that time I was quietly falling '
                                'apart. On the outside I looked fine. Inside, I was exhausted, '
                                'ashamed, and completely alone with it.\n\n'
                                'Getting clean took everything I had. I am two years into that '
                                'now, and what saved me was not some clever program. It was '
                                'finally not being alone with my own head at three in the '
                                'morning.\n\n'
                                'I built MindCore for the person I used to be. Someone who '
                                'needed a place to talk when no one was awake to listen, and no '
                                'judgement was waiting on the other side. Whatever you are '
                                'carrying tonight, you do not have to carry it alone. I mean '
                                'that.',
                                style: tt.bodySmall?.copyWith(
                                    height: 1.55, color: _subtle(isDark)),
                              ),
                              const SizedBox(height: 8),
                              Text('Keith, founder',
                                  style: tt.bodySmall?.copyWith(
                                      fontWeight: FontWeight.w700,
                                      color: AppColors.mintDeep)),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  GlassCard(
                    glowColor: AppColors.primary.withValues(alpha: 0.12),
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      children: [
                        _TrustLine(
                            text: 'Someone to talk to, any hour of the day',
                            isDark: isDark,
                            tt: tt),
                        const SizedBox(height: 12),
                        _TrustLine(
                            text: 'Private by design. Your words never train AI',
                            isDark: isDark,
                            tt: tt),
                        const SizedBox(height: 12),
                        _TrustLine(
                            text: 'No ads, ever. No data selling',
                            isDark: isDark,
                            tt: tt),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          _PrimaryButton(label: 'Continue', onTap: widget.onFinish),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  // ── Small helpers ───────────────────────────────────────────────────────────

  Color _subtle(bool isDark) => isDark
      ? Colors.white.withValues(alpha: 0.60)
      : const Color(0xFF475467);

  Widget _eyebrow(String text) => Text(
        text,
        style: TextStyle(
          color: AppColors.primary,
          fontWeight: FontWeight.w800,
          fontSize: 12,
          letterSpacing: 1.6,
        ),
      );

  String _shortTiming(String timing) {
    if (timing.contains('night')) return 'at night';
    if (timing.contains('morning')) return 'in the mornings';
    if (timing.contains('middle')) return 'during the day';
    return 'at random times';
  }
}

// ── Reusable widgets ──────────────────────────────────────────────────────────

class _PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final bool enabled;
  const _PrimaryButton(
      {required this.label, required this.onTap, this.enabled = true});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: enabled ? onTap : null,
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primary,
          disabledBackgroundColor: AppColors.primary.withValues(alpha: 0.35),
          minimumSize: const Size.fromHeight(54),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: Text(label,
            style: const TextStyle(
                color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
      ),
    );
  }
}

class _RoundIcon extends StatelessWidget {
  final IconData icon;
  final bool isDark;
  final VoidCallback onTap;
  const _RoundIcon(
      {required this.icon, required this.isDark, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 32,
        height: 32,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isDark
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.black.withValues(alpha: 0.05),
        ),
        child: Icon(icon,
            size: 15,
            color: isDark
                ? Colors.white.withValues(alpha: 0.75)
                : Colors.black.withValues(alpha: 0.6)),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  final String emoji;
  final String label;
  final bool selected;
  final bool isDark;
  final TextTheme tt;
  final VoidCallback onTap;
  const _Pill({
    required this.emoji,
    required this.label,
    required this.selected,
    required this.isDark,
    required this.tt,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected
              ? AppColors.primary.withValues(alpha: 0.14)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.05)
                  : Colors.black.withValues(alpha: 0.04)),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : (isDark
                    ? Colors.white.withValues(alpha: 0.12)
                    : Colors.black.withValues(alpha: 0.10)),
            width: selected ? 1.6 : 0.8,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 7),
            Text(label,
                style: tt.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: selected
                      ? AppColors.primary
                      : (isDark ? Colors.white : const Color(0xFF0E1320)),
                )),
          ],
        ),
      ),
    );
  }
}

class _OptionRow extends StatelessWidget {
  final String emoji;
  final String label;
  final bool selected;
  final bool isDark;
  final TextTheme tt;
  final VoidCallback onTap;
  const _OptionRow({
    required this.emoji,
    required this.label,
    required this.selected,
    required this.isDark,
    required this.tt,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 160),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(15),
          color: selected
              ? AppColors.primary.withValues(alpha: 0.12)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.05)
                  : Colors.black.withValues(alpha: 0.04)),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : (isDark
                    ? Colors.white.withValues(alpha: 0.12)
                    : Colors.black.withValues(alpha: 0.10)),
            width: selected ? 1.6 : 0.8,
          ),
        ),
        child: Row(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 19)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label,
                  style: tt.bodyLarge?.copyWith(
                    fontWeight: FontWeight.w600,
                    color: isDark ? Colors.white : const Color(0xFF0E1320),
                  )),
            ),
            if (selected)
              Icon(Icons.check_circle_rounded,
                  color: AppColors.primary, size: 20),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final TextTheme tt;
  final bool isDark;
  const _InfoRow({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
    required this.tt,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 34,
          height: 34,
          decoration: BoxDecoration(
              shape: BoxShape.circle, color: color.withValues(alpha: 0.12)),
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
                      color:
                          isDark ? Colors.white : const Color(0xFF0E1320))),
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

class _TrustLine extends StatelessWidget {
  final String text;
  final bool isDark;
  final TextTheme tt;
  const _TrustLine(
      {required this.text, required this.isDark, required this.tt});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(Icons.check_circle_rounded, color: AppColors.mintDeep, size: 20),
        const SizedBox(width: 12),
        Expanded(
          child: Text(text,
              style: tt.bodyMedium?.copyWith(
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}

class _TypingDots extends StatefulWidget {
  const _TypingDots();
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  @override
  void initState() {
    super.initState();
    _c = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1100))
      ..repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 18,
      child: AnimatedBuilder(
        animation: _c,
        builder: (context, _) {
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(3, (i) {
              final t = (_c.value - i * 0.2) % 1.0;
              final o = t < 0.5 ? 0.3 + t : 0.3 + (1 - t);
              return Padding(
                padding: const EdgeInsets.only(right: 5),
                child: Opacity(
                  opacity: o.clamp(0.3, 1.0),
                  child: Container(
                    width: 7,
                    height: 7,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.mintDeep,
                    ),
                  ),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
