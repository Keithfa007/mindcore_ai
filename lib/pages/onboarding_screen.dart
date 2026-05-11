// lib/pages/onboarding_screen.dart
//
// First-launch onboarding — 8 stages:
//  0  Orb reveal + tagline
//  1  Mission statement
//  2  Feature carousel
//  3  About you (name, current feeling, what brings you here)
//  4  Support preferences (support style, openness, initial note)
//  5  Voice selection
//  6  Disclaimer
//  7  Notification permission

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/mood_orb.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/persona_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/user_profile_service.dart';

enum _Stage {
  orb, mission, features,
  aboutYou, supportPrefs,
  voiceSelect, disclaimer, notifications,
}

// ── Data models ────────────────────────────────────────────────────────────────────

class _Chip {
  final String emoji;
  final String label;
  final bool feminineHint;
  const _Chip(this.emoji, this.label, {this.feminineHint = false});
}

const _feelings = [
  _Chip('😔', 'Not great'),
  _Chip('😰', 'Anxious or stressed'),
  _Chip('😐', 'Okay, just curious'),
  _Chip('😴', 'Exhausted'),
  _Chip('💪', 'Ready to work on myself'),
  _Chip('🌊', 'Going through something big'),
];

const _reasons = [
  _Chip('😔', 'Anxiety or stress'),
  _Chip('😞', 'Low mood or depression'),
  _Chip('💪', 'Recovery from alcohol or substances'),
  _Chip('🌙', 'Perimenopause or menopause',     feminineHint: true),
  _Chip('🌸', "Women's mental health",           feminineHint: true),
  _Chip('🧠', 'ADHD or focus'),
  _Chip('😴', 'Sleep problems'),
  _Chip('💔', 'Relationship or life difficulty'),
  _Chip('💙', 'I just need someone to talk to'),
];

const _supportStyles = [
  _Chip('🤝', 'Just listen — I need to feel heard'),
  _Chip('💡', 'Help me understand myself better'),
  _Chip('🛠️', 'Give me practical tools and techniques'),
  _Chip('🔀', 'It depends on the day — mix it up'),
];

const _openness = [
  _Chip('🔓', 'Very open — I will share anything'),
  _Chip('🔐', 'Somewhere in between'),
  _Chip('🛡️', 'Quite private — I take it slowly'),
];

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onFinish;
  const OnboardingScreen({super.key, required this.onFinish});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen>
    with TickerProviderStateMixin {

  _Stage _stage = _Stage.orb;

  // ── Orb animations
  late final AnimationController _orbCtrl;
  late final Animation<double> _orbFade;
  late final Animation<double> _taglineFade;
  late final Animation<Offset>  _taglineSlide;

  // ── Mission animations
  late final AnimationController _missionCtrl;
  late final Animation<double> _l1Fade, _l2Fade, _l3Fade;
  late final Animation<Offset>  _l1Slide, _l2Slide, _l3Slide;

  // ── Feature carousel
  final PageController _pageCtrl = PageController();
  int _featureIndex = 0;

  // ── About You answers
  final _nameCtrl = TextEditingController();
  int? _selectedFeelingIdx;
  final Set<int> _selectedReasonIdxs = {};

  // ── Support preferences answers
  int? _selectedSupportIdx;
  int? _selectedOpennessIdx;
  final _noteCtrl = TextEditingController();

  // ── Voice selection
  String _selectedGender = 'male';

  // ── Notifications
  bool _notifChosen = false;

  // ── Stage fade
  late final AnimationController _stageFadeCtrl;
  late final Animation<double>   _stageFade;

  @override
  void initState() {
    super.initState();
    _orbCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 2200));
    _orbFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _orbCtrl,
            curve: const Interval(0.0, 0.60, curve: Curves.easeOut)));
    _taglineFade = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _orbCtrl,
            curve: const Interval(0.55, 1.0, curve: Curves.easeOut)));
    _taglineSlide =
        Tween<Offset>(begin: const Offset(0, 0.08), end: Offset.zero)
            .animate(CurvedAnimation(parent: _orbCtrl,
                curve: const Interval(0.55, 1.0, curve: Curves.easeOut)));

    _missionCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1800));
    Interval iv(double s, double e) => Interval(s, e, curve: Curves.easeOut);
    Tween<Offset> st() =>
        Tween<Offset>(begin: const Offset(0, 0.10), end: Offset.zero);
    _l1Fade  = Tween<double>(begin: 0, end: 1).animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.0,  0.40)));
    _l2Fade  = Tween<double>(begin: 0, end: 1).animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.28, 0.65)));
    _l3Fade  = Tween<double>(begin: 0, end: 1).animate(
        CurvedAnimation(parent: _missionCtrl, curve: iv(0.55, 0.90)));
    _l1Slide = st().animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.0,  0.40)));
    _l2Slide = st().animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.28, 0.65)));
    _l3Slide = st().animate(CurvedAnimation(parent: _missionCtrl, curve: iv(0.55, 0.90)));

    _stageFadeCtrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 400), value: 1.0);
    _stageFade = CurvedAnimation(parent: _stageFadeCtrl, curve: Curves.easeInOut);

    _orbCtrl.forward();
  }

  @override
  void dispose() {
    _orbCtrl.dispose();
    _missionCtrl.dispose();
    _stageFadeCtrl.dispose();
    _pageCtrl.dispose();
    _nameCtrl.dispose();
    _noteCtrl.dispose();
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
      case _Stage.orb:          await _goToStage(_Stage.mission);      break;
      case _Stage.mission:      await _goToStage(_Stage.features);     break;
      case _Stage.features:
        if (_featureIndex < 2) {
          _pageCtrl.nextPage(
              duration: const Duration(milliseconds: 320),
              curve: Curves.easeOutCubic);
        } else {
          await _goToStage(_Stage.aboutYou);
        }
        break;
      case _Stage.aboutYou:
        // Auto-suggest voice based on feminine reasons
        final hasFemine = _selectedReasonIdxs.any((i) => _reasons[i].feminineHint);
        if (hasFemine) setState(() => _selectedGender = 'female');
        await _goToStage(_Stage.supportPrefs);
        break;
      case _Stage.supportPrefs:
        await _saveAllPreferences();
        await _goToStage(_Stage.voiceSelect);
        break;
      case _Stage.voiceSelect:
        await _saveVoicePreference();
        await _goToStage(_Stage.disclaimer);
        break;
      case _Stage.disclaimer:   await _goToStage(_Stage.notifications);break;
      case _Stage.notifications: widget.onFinish();                    break;
    }
  }

  Future<void> _saveAllPreferences() async {
    // Save profile
    await UserProfileService.saveProfile(
      name:         _nameCtrl.text.trim(),
      feeling:      _selectedFeelingIdx != null
          ? '${_feelings[_selectedFeelingIdx!].emoji} ${_feelings[_selectedFeelingIdx!].label}'
          : '',
      reasons:      _selectedReasonIdxs.map((i) => _reasons[i].label).toList(),
      supportStyle: _selectedSupportIdx != null
          ? _supportStyles[_selectedSupportIdx!].label
          : '',
      openness:     _selectedOpennessIdx != null
          ? _openness[_selectedOpennessIdx!].label
          : '',
      initialNote:  _noteCtrl.text.trim(),
    );
    // Set persona
    final isFeminine = _selectedReasonIdxs.any((i) => _reasons[i].feminineHint) ||
        _selectedGender == 'female';
    await PersonaService.setPersonaStyle(
        isFeminine ? PersonaStyle.feminine : PersonaStyle.standard);
  }

  Future<void> _saveVoicePreference() async {
    await LiveVoicePreferences.instance.load();
    await LiveVoicePreferences.instance.setCompanionGender(_selectedGender);
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
      case _Stage.orb:          return _buildOrbStage(tt, isDark);
      case _Stage.mission:      return _buildMissionStage(tt, isDark);
      case _Stage.features:     return _buildFeaturesStage(tt, isDark);
      case _Stage.aboutYou:     return _buildAboutYouStage(tt, isDark);
      case _Stage.supportPrefs: return _buildSupportPrefsStage(tt, isDark);
      case _Stage.voiceSelect:  return _buildVoiceSelectStage(tt, isDark);
      case _Stage.disclaimer:   return _buildDisclaimerStage(tt, isDark);
      case _Stage.notifications:return _buildNotificationsStage(tt, isDark);
    }
  }

  // ── Stage 0: Orb ─────────────────────────────────────────────────────────────
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
              builder: (_, child) => Opacity(opacity: _orbFade.value, child: child),
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
                  Text('You deserve to feel better.',
                      textAlign: TextAlign.center,
                      style: tt.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                        color: isDark ? Colors.white : const Color(0xFF0E1320),
                        letterSpacing: -0.8,
                      )),
                  const SizedBox(height: 12),
                  Text('A calm, private space — always in your pocket.',
                      textAlign: TextAlign.center,
                      style: tt.bodyMedium?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.55)
                            : const Color(0xFF475467),
                        height: 1.5,
                      )),
                ],
              ),
            ),
            const Spacer(flex: 2),
            AnimatedBuilder(
              animation: _taglineFade,
              builder: (_, child) => Opacity(opacity: _taglineFade.value, child: child),
              child: Text('Tap anywhere to continue',
                  style: tt.labelSmall?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.30)
                        : Colors.black.withValues(alpha: 0.30),
                    letterSpacing: 0.5,
                  )),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  // ── Stage 1: Mission ────────────────────────────────────────────────────────
  Widget _buildMissionStage(TextTheme tt, bool isDark) {
    final textColor   = isDark ? Colors.white : const Color(0xFF0E1320);
    final subtleColor = isDark
        ? Colors.white.withValues(alpha: 0.60)
        : const Color(0xFF475467);
    Widget sl(Animation<double> f, Animation<Offset> s, String t, TextStyle? st) =>
        AnimatedBuilder(
          animation: f,
          builder: (_, child) => Opacity(
              opacity: f.value,
              child: SlideTransition(position: s, child: child)),
          child: Text(t, textAlign: TextAlign.center, style: st),
        );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 2),
          sl(_l1Fade, _l1Slide,
              'MindCore AI was built for the moments\nwhen everything feels like too much.',
              tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900, color: textColor,
                  letterSpacing: -0.6, height: 1.25)),
          const SizedBox(height: 24),
          sl(_l2Fade, _l2Slide,
              'Not to fix you.\nJust to be there with you.',
              tt.titleLarge?.copyWith(
                  fontWeight: FontWeight.w700, color: subtleColor, height: 1.4)),
          const SizedBox(height: 24),
          sl(_l3Fade, _l3Slide, 'Calm. Private. Always ready.',
              tt.bodyLarge?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : const Color(0xFF94A3B8),
                  letterSpacing: 0.3)),
          const Spacer(flex: 2),
          _BottomButton(
              label: 'Continue', onTap: _handleContinue, color: AppColors.primary),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  // ── Stage 2: Features ───────────────────────────────────────────────────────
  static const _features = [
    _FData(icon: Icons.psychology_rounded, color: Color(0xFF4D7CFF),
        title: 'AI that actually listens',
        body: "Not scripted responses. MindCore reads your mood and history — and responds accordingly."),
    _FData(icon: Icons.self_improvement_rounded, color: Color(0xFF32D0BE),
        title: 'Tools that work in real time',
        body: 'Guided breathing, voice chat, grounding audio, and a daily reset — one tap away.'),
    _FData(icon: Icons.insights_rounded, color: Color(0xFF9B7FFF),
        title: 'Patterns that help you understand yourself',
        body: 'Weekly mood reports, streak tracking, and pattern detection.'),
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
              height: 6, width: active ? 22 : 6,
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
                                  color: f.color.withValues(alpha: 0.35), width: 1.5),
                            ),
                            child: Icon(f.icon, color: f.color, size: 34),
                          ),
                          const SizedBox(height: 22),
                          Text(f.title,
                              textAlign: TextAlign.center,
                              style: tt.titleLarge?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  color: isDark ? Colors.white : const Color(0xFF0E1320),
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
            label: isLast ? 'Tell us about you →' : 'Next',
            onTap: _handleContinue,
            color: _features[_featureIndex].color,
          ),
        ),
      ],
    );
  }

  // ── Stage 3: About You ──────────────────────────────────────────────────
  Widget _buildAboutYouStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          Text('Let\'s get to know you',
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  letterSpacing: -0.6)),
          const SizedBox(height: 6),
          Text('The more you share, the better your experience from day one.',
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.55)
                      : const Color(0xFF475467))),
          const SizedBox(height: 20),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name
                  Text('What should I call you? (optional)',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _nameCtrl,
                    textCapitalization: TextCapitalization.words,
                    decoration: InputDecoration(
                      hintText: 'Your first name or nickname',
                      filled: true,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 14),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Feeling
                  Text('How are you feeling right now?',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8, runSpacing: 8,
                    children: List.generate(_feelings.length, (i) {
                      final f = _feelings[i];
                      final sel = _selectedFeelingIdx == i;
                      return _SelectChip(
                        emoji: f.emoji, label: f.label,
                        selected: sel,
                        onTap: () => setState(() =>
                            _selectedFeelingIdx = sel ? null : i),
                        isDark: isDark, tt: tt,
                      );
                    }),
                  ),
                  const SizedBox(height: 24),

                  // Reasons (multi-select)
                  Text('What brings you to MindCore AI?',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('Select all that apply',
                      style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.45)
                              : const Color(0xFF94A3B8))),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8, runSpacing: 8,
                    children: List.generate(_reasons.length, (i) {
                      final r = _reasons[i];
                      final sel = _selectedReasonIdxs.contains(i);
                      return _SelectChip(
                        emoji: r.emoji, label: r.label,
                        selected: sel,
                        onTap: () => setState(() => sel
                            ? _selectedReasonIdxs.remove(i)
                            : _selectedReasonIdxs.add(i)),
                        isDark: isDark, tt: tt,
                      );
                    }),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
          _BottomButton(
              label: 'Continue →', onTap: _handleContinue, color: AppColors.primary),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Stage 4: Support preferences ──────────────────────────────────────────
  Widget _buildSupportPrefsStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 20),
          Text('How can I help you best?',
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  letterSpacing: -0.6)),
          const SizedBox(height: 6),
          Text('This shapes how I respond to you from day one.',
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.55)
                      : const Color(0xFF475467))),
          const SizedBox(height: 20),
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Support style
                  Text('When you are struggling, what helps most?',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  ...List.generate(_supportStyles.length, (i) {
                    final s = _supportStyles[i];
                    final sel = _selectedSupportIdx == i;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _OptionRow(
                        emoji: s.emoji, label: s.label,
                        selected: sel,
                        onTap: () => setState(() =>
                            _selectedSupportIdx = sel ? null : i),
                        isDark: isDark, tt: tt,
                      ),
                    );
                  }),
                  const SizedBox(height: 24),

                  // Openness
                  Text('How comfortable are you sharing?',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  ...List.generate(_openness.length, (i) {
                    final o = _openness[i];
                    final sel = _selectedOpennessIdx == i;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: _OptionRow(
                        emoji: o.emoji, label: o.label,
                        selected: sel,
                        onTap: () => setState(() =>
                            _selectedOpennessIdx = sel ? null : i),
                        isDark: isDark, tt: tt,
                      ),
                    );
                  }),
                  const SizedBox(height: 24),

                  // Initial note
                  Text('Anything you want me to know before we start? (optional)',
                      style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text('I will remember this and use it from your very first conversation.',
                      style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.45)
                              : const Color(0xFF94A3B8))),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _noteCtrl,
                    maxLines: 3,
                    decoration: InputDecoration(
                      hintText: 'Share as much or as little as you like…',
                      filled: true,
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 14),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(14),
                        borderSide: BorderSide.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            ),
          ),
          _BottomButton(
              label: 'Continue →', onTap: _handleContinue, color: AppColors.primary),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Stage 5: Voice selection ──────────────────────────────────────────────
  Widget _buildVoiceSelectStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(),
          Icon(Icons.record_voice_over_rounded,
              color: AppColors.primary, size: 48),
          const SizedBox(height: 20),
          Text('Choose your companion voice',
              textAlign: TextAlign.center,
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  letterSpacing: -0.6)),
          const SizedBox(height: 10),
          Text('You can change this any time in settings.',
              textAlign: TextAlign.center,
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.55)
                      : const Color(0xFF475467))),
          const SizedBox(height: 32),
          Row(
            children: [
              Expanded(child: _VoiceCard(
                  gender: 'male', title: 'Calm Male',
                  subtitle: 'Deep, grounded, steady',
                  selected: _selectedGender == 'male',
                  onTap: () => setState(() => _selectedGender = 'male'),
                  tt: tt, isDark: isDark)),
              const SizedBox(width: 14),
              Expanded(child: _VoiceCard(
                  gender: 'female', title: 'Warm Female',
                  subtitle: 'Warm, relaxing, gentle',
                  selected: _selectedGender == 'female',
                  onTap: () => setState(() => _selectedGender = 'female'),
                  tt: tt, isDark: isDark)),
            ],
          ),
          const Spacer(),
          _BottomButton(
              label: 'Continue →', onTap: _handleContinue, color: AppColors.primary),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  // ── Stage 6: Disclaimer ──────────────────────────────────────────────────
  Widget _buildDisclaimerStage(TextTheme tt, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 24),
          Container(
            width: 64, height: 64,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: const Color(0xFFFF6B6B).withValues(alpha: 0.12),
              border: Border.all(
                  color: const Color(0xFFFF6B6B).withValues(alpha: 0.35), width: 1.5),
            ),
            child: const Icon(Icons.info_outline_rounded,
                color: Color(0xFFFF6B6B), size: 30),
          ),
          const SizedBox(height: 16),
          Text('Before you begin',
              textAlign: TextAlign.center,
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  letterSpacing: -0.6)),
          const SizedBox(height: 20),
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
                          icon: Icons.smart_toy_rounded, color: AppColors.primary,
                          title: 'Not a medical service',
                          body: 'MindCore AI is a personal wellness companion, not a licensed therapy or medical platform.',
                          tt: tt, isDark: isDark,
                        ),
                        const SizedBox(height: 14),
                        _DisclaimerRow(
                          icon: Icons.person_rounded, color: AppColors.mintDeep,
                          title: 'Not a replacement for professional help',
                          body: 'AI responses are not a substitute for advice from a qualified mental health professional.',
                          tt: tt, isDark: isDark,
                        ),
                        const SizedBox(height: 14),
                        _DisclaimerRow(
                          icon: Icons.warning_amber_rounded, color: const Color(0xFFFF6B6B),
                          title: 'In a crisis or emergency',
                          body: 'If you are in immediate danger, please contact your local emergency services or a crisis helpline.',
                          tt: tt, isDark: isDark,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFF6B6B).withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                          color: const Color(0xFFFF6B6B).withValues(alpha: 0.25)),
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
                          '• Malta: 1579\n• USA/Canada: 988\n• UK & Ireland: 116 123 (Samaritans)\n• Australia: 13 11 14 (Lifeline)\n• International: findahelpline.com',
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
              child: const Text('I understand — Continue',
                  style: TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  // ── Stage 7: Notifications ──────────────────────────────────────────────
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
                  color: AppColors.primary.withValues(alpha: 0.30), width: 1.5),
            ),
            child: Icon(Icons.notifications_rounded, color: AppColors.primary, size: 38),
          ),
          const SizedBox(height: 28),
          Text('Stay connected to yourself',
              textAlign: TextAlign.center,
              style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                  letterSpacing: -0.6)),
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
                  Icon(Icons.check_circle_rounded, color: AppColors.mintDeep, size: 22),
                  const SizedBox(width: 8),
                  Text('Saved — taking you in…',
                      style: tt.bodyMedium?.copyWith(
                          color: AppColors.mintDeep, fontWeight: FontWeight.w700)),
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
                icon: const Icon(Icons.notifications_active_rounded, color: Colors.white),
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
                child: Text('Not right now',
                    style: TextStyle(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.55)
                          : const Color(0xFF64748B),
                    )),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ],
      ),
    );
  }
}

// ── Shared widgets ────────────────────────────────────────────────────────────────

class _BottomButton extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final Color color;
  const _BottomButton({required this.label, required this.onTap, required this.color});
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          backgroundColor: color,
          minimumSize: const Size.fromHeight(54),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: Text(label,
            style: const TextStyle(
                color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
      ),
    );
  }
}

class _SelectChip extends StatelessWidget {
  final String emoji;
  final String label;
  final bool selected;
  final VoidCallback onTap;
  final bool isDark;
  final TextTheme tt;
  const _SelectChip({
    required this.emoji, required this.label, required this.selected,
    required this.onTap, required this.isDark, required this.tt,
  });
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () { HapticFeedback.selectionClick(); onTap(); },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(100),
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
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 6),
            Text(label,
                style: tt.bodySmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: selected
                      ? AppColors.primary
                      : (isDark ? Colors.white : const Color(0xFF0E1320)),
                )),
            if (selected) ...[
              const SizedBox(width: 4),
              Icon(Icons.check, color: AppColors.primary, size: 14),
            ],
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
  final VoidCallback onTap;
  final bool isDark;
  final TextTheme tt;
  const _OptionRow({
    required this.emoji, required this.label, required this.selected,
    required this.onTap, required this.isDark, required this.tt,
  });
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () { HapticFeedback.selectionClick(); onTap(); },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected
              ? AppColors.primary.withValues(alpha: 0.10)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.04)
                  : Colors.black.withValues(alpha: 0.03)),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : (isDark
                    ? Colors.white.withValues(alpha: 0.10)
                    : Colors.black.withValues(alpha: 0.08)),
            width: selected ? 1.6 : 0.8,
          ),
        ),
        child: Row(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 20)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label,
                  style: tt.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: selected
                          ? AppColors.primary
                          : (isDark ? Colors.white : const Color(0xFF0E1320)))),
            ),
            if (selected)
              Icon(Icons.check_circle_rounded, color: AppColors.primary, size: 18),
          ],
        ),
      ),
    );
  }
}

class _VoiceCard extends StatelessWidget {
  final String gender;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;
  final bool isDark;
  final TextTheme tt;
  const _VoiceCard({
    required this.gender, required this.title, required this.subtitle,
    required this.selected, required this.onTap,
    required this.isDark, required this.tt,
  });
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () { HapticFeedback.selectionClick(); onTap(); },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 16),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          color: selected
              ? AppColors.primary.withValues(alpha: 0.12)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.05)
                  : Colors.black.withValues(alpha: 0.03)),
          border: Border.all(
            color: selected
                ? AppColors.primary
                : (isDark
                    ? Colors.white.withValues(alpha: 0.12)
                    : Colors.black.withValues(alpha: 0.10)),
            width: selected ? 2 : 0.8,
          ),
        ),
        child: Column(
          children: [
            const Text('🎙️', style: TextStyle(fontSize: 32)),
            const SizedBox(height: 12),
            Text(title,
                style: tt.titleMedium?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: selected
                        ? AppColors.primary
                        : (isDark ? Colors.white : const Color(0xFF0E1320)))),
            const SizedBox(height: 6),
            Text(subtitle,
                textAlign: TextAlign.center,
                style: tt.bodySmall?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.50)
                        : const Color(0xFF475467),
                    height: 1.5)),
            if (selected) ...[const SizedBox(height: 12),
              Icon(Icons.check_circle_rounded, color: AppColors.primary, size: 22)],
          ],
        ),
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
  const _DisclaimerRow({
    required this.icon, required this.color, required this.title,
    required this.body, required this.tt, required this.isDark,
  });
  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 34, height: 34,
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
                      color: isDark ? Colors.white : const Color(0xFF0E1320))),
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

class _FData {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  const _FData({required this.icon, required this.color, required this.title, required this.body});
}
