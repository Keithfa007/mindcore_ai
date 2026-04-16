// lib/pages/sos_screen.dart
//
// Quick Reset — one-tap grounding sequence.
// Step 1: Breathing (follow the orb) — with voice guidance
// Step 2: 5-4-3-2-1 grounding technique
// Step 3: Calming audio

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:wakelock_plus/wakelock_plus.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

enum _SosStep { breathe, grounding, audio }

const _kCalmColor = Color(0xFF2D7DD2);

const _groundingItems = [
  _GroundingItem('5 things you can see',  Icons.visibility_rounded,  Color(0xFF185FA5)),
  _GroundingItem('4 things you can touch', Icons.touch_app_rounded,  Color(0xFF0F6E56)),
  _GroundingItem('3 things you can hear',  Icons.hearing_rounded,    Color(0xFF534AB7)),
  _GroundingItem('2 things you can smell', Icons.air_rounded,        Color(0xFF854F0B)),
  _GroundingItem('1 thing you can taste',  Icons.restaurant_rounded, Color(0xFF993556)),
];

class _GroundingItem {
  final String label;
  final IconData icon;
  final Color color;
  const _GroundingItem(this.label, this.icon, this.color);
}

class SosScreen extends StatefulWidget {
  const SosScreen({super.key});
  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> with TickerProviderStateMixin {
  _SosStep _step = _SosStep.breathe;

  // Breathing — 8s cycle (4 inhale / 4 exhale), auto-advances after 60s
  late final AnimationController _breathCtrl;
  Timer? _breathTimer;
  int _breathSecondsLeft = 60;

  // Voice guidance — tracks last spoken phase to avoid repeating
  bool _lastWasInhale = false;
  bool _voiceStarted = false;

  // Audio (Step 3)
  final AudioPlayer _player = AudioPlayer();
  bool _audioPlaying = false;

  @override
  void initState() {
    super.initState();
    // Keep screen on for the entire SOS session
    WakelockPlus.enable();

    _breathCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat()..addListener(_onBreathTick);

    // Speak intro after a short delay so screen has rendered
    Future.delayed(const Duration(milliseconds: 600), _speakIntro);

    _breathTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        _breathSecondsLeft--;
        if (_breathSecondsLeft <= 0) _advanceStep();
      });
    });
  }

  // Speak a warm intro then start phase guidance
  Future<void> _speakIntro() async {
    if (!mounted) return;
    await OpenAiTtsService.instance.speak(
      'You are safe. Just breathe with me. Breathe in slowly...',
      moodLabel: 'calm',
      messageId: 'sos_intro',
      surface: TtsSurface.breathe,
    );
    _voiceStarted = true;
  }

  // Fires on every animation tick — speaks when phase changes
  void _onBreathTick() {
    if (!_voiceStarted) return;
    final isInhale = _breathCtrl.value < 0.5;
    if (isInhale == _lastWasInhale) return;
    _lastWasInhale = isInhale;
    _speakPhase(isInhale);
  }

  Future<void> _speakPhase(bool isInhale) async {
    if (!mounted || _step != _SosStep.breathe) return;
    final text = isInhale
        ? 'Breathe in slowly and gently...'
        : 'Breathe out... let it all go...';
    await OpenAiTtsService.instance.speak(
      text,
      moodLabel: 'calm',
      messageId: 'sos_phase',
      surface: TtsSurface.breathe,
    );
  }

  @override
  void dispose() {
    _breathCtrl.removeListener(_onBreathTick);
    _breathCtrl.dispose();
    _breathTimer?.cancel();
    _player.dispose();
    OpenAiTtsService.instance.stop();
    WakelockPlus.disable();
    super.dispose();
  }

  void _advanceStep() {
    _breathTimer?.cancel();
    OpenAiTtsService.instance.stop();
    if (_step == _SosStep.breathe) {
      setState(() => _step = _SosStep.grounding);
    } else if (_step == _SosStep.grounding) {
      _startAudio();
      setState(() => _step = _SosStep.audio);
    }
  }

  Future<void> _startAudio() async {
    try {
      await _player.play(AssetSource('audio/Panic Calmer.mp3'));
      setState(() => _audioPlaying = true);
      _player.onPlayerComplete
          .listen((_) => setState(() => _audioPlaying = false));
    } catch (_) {}
  }

  Future<void> _stopAudio() async {
    await _player.stop();
    setState(() => _audioPlaying = false);
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs     = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: cs.surface,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                child: Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.close_rounded,
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.50)
                              : Colors.black.withValues(alpha: 0.40)),
                      onPressed: () {
                        _stopAudio();
                        OpenAiTtsService.instance.stop();
                        Navigator.of(context).pop();
                      },
                    ),
                    const SizedBox(width: 4),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Quick Reset',
                            style: tt.titleMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF0E1320))),
                        Text('3 steps to calm',
                            style: tt.bodySmall?.copyWith(
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.40)
                                    : Colors.black.withValues(alpha: 0.35))),
                      ],
                    ),
                    const Spacer(),
                    // Voice indicator
                    if (_step == _SosStep.breathe)
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: Icon(
                          Icons.record_voice_over_rounded,
                          size: 18,
                          color: _kCalmColor.withValues(alpha: 0.55),
                        ),
                      ),
                  ],
                ),
              ),

              // Step bar
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 4),
                child: _StepBar(current: _step),
              ),

              // Step content
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 600),
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeIn,
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
      case _SosStep.breathe:
        return _BreatheStep(
          key: const ValueKey('b'),
          ctrl: _breathCtrl,
          onSkip: _advanceStep,
          tt: tt, isDark: isDark,
        );
      case _SosStep.grounding:
        return _GroundingStep(
          key: const ValueKey('g'),
          onNext: _advanceStep,
          tt: tt, isDark: isDark,
        );
      case _SosStep.audio:
        return _AudioStep(
          key: const ValueKey('a'),
          isPlaying: _audioPlaying,
          onPlay: _startAudio,
          onStop: _stopAudio,
          onClose: () { _stopAudio(); Navigator.of(context).pop(); },
          tt: tt, isDark: isDark,
        );
    }
  }
}

// ── Step 1: Breathing ─────────────────────────────────────────────────────────

class _BreatheStep extends StatelessWidget {
  final AnimationController ctrl;
  final VoidCallback onSkip;
  final TextTheme tt;
  final bool isDark;
  const _BreatheStep({
    super.key,
    required this.ctrl, required this.onSkip,
    required this.tt, required this.isDark,
  });

  static double _lerp(double a, double b, double t) => a + (b - a) * t;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 16),
        Text(
          'Step 1  —  Breathe',
          style: tt.labelSmall?.copyWith(
              fontWeight: FontWeight.w600,
              letterSpacing: 1.0,
              color: _kCalmColor.withValues(alpha: 0.70)),
        ),
        const SizedBox(height: 6),
        Text(
          'Put your phone down and just listen.',
          textAlign: TextAlign.center,
          style: tt.bodyMedium?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : Colors.black.withValues(alpha: 0.40),
              fontStyle: FontStyle.italic),
        ),

        // Orb
        Expanded(
          child: Center(
            child: AnimatedBuilder(
              animation: ctrl,
              builder: (_, __) {
                final v        = ctrl.value;
                final isInhale = v < 0.5;
                final localP   = isInhale ? v / 0.5 : (v - 0.5) / 0.5;
                final scale = isInhale
                    ? _lerp(0.65, 0.93,
                        Curves.easeInOut.transform(localP))
                    : _lerp(0.93, 0.65,
                        Curves.easeInOut.transform(localP));

                return SizedBox(
                  width: 260, height: 260,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      Transform.scale(
                        scale: scale * 1.45,
                        child: Container(
                          width: 190, height: 190,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _kCalmColor.withValues(alpha: 0.04),
                          ),
                        ),
                      ),
                      Transform.scale(
                        scale: scale * 1.22,
                        child: Container(
                          width: 190, height: 190,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: _kCalmColor.withValues(alpha: 0.08),
                          ),
                        ),
                      ),
                      Transform.scale(
                        scale: scale,
                        child: Container(
                          width: 190, height: 190,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(colors: [
                              Colors.white.withValues(alpha: 0.28),
                              _kCalmColor.withValues(alpha: 0.50),
                              _kCalmColor.withValues(alpha: 0.20),
                              _kCalmColor.withValues(alpha: 0.03),
                            ], stops: const [0.0, 0.25, 0.60, 1.0]),
                            border: Border.all(
                              color: _kCalmColor.withValues(alpha: 0.22),
                              width: 1.0,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),

        SizedBox(
          height: 32,
          child: AnimatedBuilder(
            animation: ctrl,
            builder: (_, __) {
              final label =
                  ctrl.value < 0.5 ? 'Breathe In' : 'Breathe Out';
              return AnimatedSwitcher(
                duration: const Duration(milliseconds: 800),
                child: Text(
                  label,
                  key: ValueKey(label),
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w300,
                    letterSpacing: 4,
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.75)
                        : const Color(0xFF1A3550),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Voice is guiding you — no need to look',
          style: tt.bodySmall?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.30)
                  : Colors.black.withValues(alpha: 0.28),
              fontStyle: FontStyle.italic),
        ),
        const SizedBox(height: 16),
        TextButton.icon(
          onPressed: onSkip,
          icon: const Icon(Icons.skip_next_rounded, size: 16),
          label: const Text('Move to grounding'),
          style: TextButton.styleFrom(
              foregroundColor: _kCalmColor.withValues(alpha: 0.70)),
        ),
        const SizedBox(height: 20),
      ],
    );
  }
}

// ── Step 2: Grounding ─────────────────────────────────────────────────────────

class _GroundingStep extends StatelessWidget {
  final VoidCallback onNext;
  final TextTheme tt;
  final bool isDark;
  const _GroundingStep({
    super.key,
    required this.onNext, required this.tt, required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Step 2  —  Ground Yourself',
              textAlign: TextAlign.center,
              style: tt.labelSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.0,
                  color: AppColors.mintDeep.withValues(alpha: 0.75))),
          const SizedBox(height: 4),
          Text(
            'Name each one slowly. There is no hurry.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.45)
                    : Colors.black.withValues(alpha: 0.40),
                fontStyle: FontStyle.italic),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.separated(
              itemCount: _groundingItems.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final item = _groundingItems[i];
                return Container(
                  decoration: BoxDecoration(
                    color: item.color.withValues(
                        alpha: isDark ? 0.10 : 0.06),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: item.color.withValues(alpha: 0.22)),
                  ),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      Container(
                        width: 32, height: 32,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: item.color.withValues(alpha: 0.14),
                          border: Border.all(
                              color: item.color.withValues(alpha: 0.30)),
                        ),
                        child: Center(
                          child: Text('${5 - i}',
                              style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w800,
                                  color: item.color)),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Icon(item.icon, color: item.color, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(item.label,
                            style: tt.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w600,
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.82)
                                    : const Color(0xFF0E1320))),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: onNext,
            icon: const Icon(Icons.headphones_rounded, size: 18),
            label: const Text('I\u2019m ready — play calming audio',
                style: TextStyle(fontWeight: FontWeight.w700)),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.mintDeep,
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14)),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Step 3: Audio ─────────────────────────────────────────────────────────────

class _AudioStep extends StatelessWidget {
  final bool isPlaying;
  final VoidCallback onPlay, onStop, onClose;
  final TextTheme tt;
  final bool isDark;
  const _AudioStep({
    super.key,
    required this.isPlaying, required this.onPlay,
    required this.onStop, required this.onClose,
    required this.tt, required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 8, 24, 24),
      child: Column(
        children: [
          Text('Step 3  —  Listen',
              style: tt.labelSmall?.copyWith(
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.0,
                  color: AppColors.violet.withValues(alpha: 0.70))),
          const SizedBox(height: 4),
          Text('A short calming audio is playing. Just be here.',
              textAlign: TextAlign.center,
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.40),
                  fontStyle: FontStyle.italic)),
          const Spacer(),
          _PulsingAudioOrb(isPlaying: isPlaying),
          const SizedBox(height: 28),
          GlassCard(
            glowColor: AppColors.glowViolet,
            child: Column(
              children: [
                Text('Panic Calmer',
                    style: tt.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700),
                    textAlign: TextAlign.center),
                const SizedBox(height: 6),
                Text(
                  'A short grounding audio for intense moments.\nJust breathe and let it wash over you.',
                  style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.50)
                          : const Color(0xFF475467),
                      height: 1.5),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    IconButton.filled(
                      onPressed: isPlaying ? onStop : onPlay,
                      style: IconButton.styleFrom(
                          backgroundColor: AppColors.violet,
                          minimumSize: const Size(56, 56)),
                      icon: Icon(
                        isPlaying
                            ? Icons.pause_rounded
                            : Icons.play_arrow_rounded,
                        color: Colors.white, size: 28,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  isPlaying ? 'Playing\u2026' : 'Tap to play',
                  style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.35)
                          : Colors.black.withValues(alpha: 0.30)),
                ),
              ],
            ),
          ),
          const Spacer(),
          FilledButton.icon(
            onPressed: onClose,
            icon: const Icon(Icons.check_rounded, size: 18),
            label: const Text('I feel calmer \u2014 close',
                style: TextStyle(fontWeight: FontWeight.w700)),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14)),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Pulsing audio orb ─────────────────────────────────────────────────────────

class _PulsingAudioOrb extends StatefulWidget {
  final bool isPlaying;
  const _PulsingAudioOrb({required this.isPlaying});
  @override
  State<_PulsingAudioOrb> createState() => _PulsingAudioOrbState();
}

class _PulsingAudioOrbState extends State<_PulsingAudioOrb>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 2200))
      ..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.90, end: 1.08)
        .animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() { _ctrl.dispose(); super.dispose(); }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Transform.scale(
        scale: widget.isPlaying ? _anim.value : 1.0,
        child: Container(
          width: 130, height: 130,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [
              Colors.white.withValues(alpha: 0.20),
              AppColors.violet.withValues(alpha: 0.45),
              AppColors.violet.withValues(alpha: 0.15),
              Colors.transparent,
            ], stops: const [0.0, 0.30, 0.65, 1.0]),
            border: Border.all(
                color: AppColors.violet.withValues(alpha: 0.35), width: 1.5),
          ),
          child: Icon(
            widget.isPlaying
                ? Icons.music_note_rounded
                : Icons.music_off_rounded,
            color: AppColors.violet.withValues(alpha: 0.80), size: 40,
          ),
        ),
      ),
    );
  }
}

// ── Step bar ───────────────────────────────────────────────────────────────────

class _StepBar extends StatelessWidget {
  final _SosStep current;
  const _StepBar({required this.current});

  @override
  Widget build(BuildContext context) {
    final colors = [_kCalmColor, AppColors.mintDeep, AppColors.violet];
    final steps  = [_SosStep.breathe, _SosStep.grounding, _SosStep.audio];
    final labels = ['Breathe', 'Ground', 'Listen'];
    final active = steps.indexOf(current);

    return Column(
      children: [
        Row(
          children: List.generate(3, (i) {
            return Expanded(
              child: Container(
                margin: EdgeInsets.only(right: i < 2 ? 6 : 0),
                height: 3,
                decoration: BoxDecoration(
                  color: i <= active
                      ? colors[i]
                      : colors[i].withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 5),
        Row(
          children: List.generate(3, (i) {
            final isActive = i == active;
            return Expanded(
              child: Text(
                labels[i],
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight:
                      isActive ? FontWeight.w700 : FontWeight.w400,
                  color: isActive
                      ? colors[i]
                      : colors[i].withValues(alpha: 0.35),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}
