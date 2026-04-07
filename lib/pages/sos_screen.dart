// lib/pages/sos_screen.dart
//
// Quick Reset — one-tap grounding sequence.
// Step 1: 60-second breathing (4s inhale / 4s exhale)
// Step 2: 5-4-3-2-1 grounding technique
// Step 3: Calming audio

import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

enum _SosStep { breathe, grounding, audio }

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

class _SosScreenState extends State<SosScreen>
    with TickerProviderStateMixin {
  _SosStep _step = _SosStep.breathe;

  // Breathing — 8s cycle (4 inhale / 4 exhale)
  late final AnimationController _breathCtrl;
  Timer? _breathTimer;
  int _breathSecondsLeft = 60;

  // Audio
  final AudioPlayer _player = AudioPlayer();
  bool _audioPlaying = false;

  static const _groundingItems = [
    _GroundingItem('5 things you can SEE',
        Icons.visibility_rounded, Color(0xFF185FA5)),
    _GroundingItem('4 things you can TOUCH',
        Icons.touch_app_rounded, Color(0xFF0F6E56)),
    _GroundingItem('3 things you can HEAR',
        Icons.hearing_rounded, Color(0xFF534AB7)),
    _GroundingItem('2 things you can SMELL',
        Icons.air_rounded, Color(0xFF854F0B)),
    _GroundingItem('1 thing you can TASTE',
        Icons.restaurant_rounded, Color(0xFF993556)),
  ];

  @override
  void initState() {
    super.initState();
    _breathCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    _breathTimer =
        Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      setState(() {
        _breathSecondsLeft--;
        if (_breathSecondsLeft <= 0) _advanceStep();
      });
    });
  }

  @override
  void dispose() {
    _breathCtrl.dispose();
    _breathTimer?.cancel();
    _player.dispose();
    super.dispose();
  }

  void _advanceStep() {
    _breathTimer?.cancel();
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
              // ── Header ────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                child: Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.close_rounded,
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.60)
                              : Colors.black.withValues(alpha: 0.45)),
                      onPressed: () {
                        _stopAudio();
                        Navigator.of(context).pop();
                      },
                    ),
                    const SizedBox(width: 4),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Quick Reset',
                            style: tt.titleMedium?.copyWith(
                                fontWeight: FontWeight.w900,
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF0E1320))),
                        Text('Grounding sequence — 3 steps',
                            style: tt.bodySmall?.copyWith(
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.45)
                                    : Colors.black.withValues(alpha: 0.40))),
                      ],
                    ),
                  ],
                ),
              ),

              // ── Step progress bar ─────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 10, 20, 4),
                child: _StepBar(current: _step),
              ),

              // ── Step content ──────────────────────────────────────
              Expanded(
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 500),
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
      case _SosStep.breathe:   return _BreatheStep(key: const ValueKey('b'), ctrl: _breathCtrl, secondsLeft: _breathSecondsLeft, onSkip: _advanceStep, tt: tt, isDark: isDark);
      case _SosStep.grounding: return _GroundingStep(key: const ValueKey('g'), onNext: _advanceStep, tt: tt, isDark: isDark);
      case _SosStep.audio:     return _AudioStep(key: const ValueKey('a'), isPlaying: _audioPlaying, onPlay: _startAudio, onStop: _stopAudio, onClose: () { _stopAudio(); Navigator.of(context).pop(); }, tt: tt, isDark: isDark);
    }
  }
}

// ── Step 1: Breathing ─────────────────────────────────────────────────────────

class _BreatheStep extends StatelessWidget {
  final AnimationController ctrl;
  final int secondsLeft;
  final VoidCallback onSkip;
  final TextTheme tt;
  final bool isDark;
  const _BreatheStep({
    super.key,
    required this.ctrl, required this.secondsLeft,
    required this.onSkip, required this.tt, required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 8),
        // Step label
        Text('STEP 1 — BREATHE',
            style: TextStyle(
                fontSize: 11, fontWeight: FontWeight.w800,
                letterSpacing: 1.5,
                color: AppColors.primary.withValues(alpha: 0.80))),
        const SizedBox(height: 4),
        Text('Follow the orb. Slow, steady breaths.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.55)
                    : const Color(0xFF475467))),
        // Breathing orb
        Expanded(
          child: Center(
            child: AnimatedBuilder(
              animation: ctrl,
              builder: (_, __) {
                final v = ctrl.value;
                final isInhale = v < 0.5;
                final localP = isInhale ? v / 0.5 : (v - 0.5) / 0.5;
                final scale = isInhale
                    ? _lerp(0.58, 1.0, Curves.easeOut.transform(localP))
                    : _lerp(1.0, 0.58, Curves.easeIn.transform(localP));
                final color = isInhale ? AppColors.primary : AppColors.violet;
                final secsInPhase = isInhale
                    ? ((0.5 - v) * 8).ceil().clamp(0, 4)
                    : ((1.0 - v) * 8).ceil().clamp(0, 4);

                return SizedBox(
                  width: 260, height: 260,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      // Outer glow
                      Transform.scale(
                        scale: scale * 1.35,
                        child: Container(
                          width: 200, height: 200,
                          decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: color.withValues(alpha: 0.05)),
                        ),
                      ),
                      // Arc ring
                      CustomPaint(
                        size: const Size(260, 260),
                        painter: _SosArcPainter(
                            progress: localP, color: color),
                      ),
                      // Main orb
                      Transform.scale(
                        scale: scale,
                        child: Container(
                          width: 190, height: 190,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            gradient: RadialGradient(colors: [
                              color.withValues(alpha: 0.60),
                              color.withValues(alpha: 0.22),
                              color.withValues(alpha: 0.04),
                            ], stops: const [0.0, 0.50, 1.0]),
                            border: Border.all(
                                color: color.withValues(alpha: 0.45),
                                width: 1.5),
                          ),
                        ),
                      ),
                      // Center text
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text('$secsInPhase',
                              style: const TextStyle(
                                  fontSize: 52,
                                  fontWeight: FontWeight.w200,
                                  color: Colors.white,
                                  height: 1.0)),
                          const SizedBox(height: 4),
                          Text(isInhale ? 'INHALE' : 'EXHALE',
                              style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: 2.5)),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
        // Timing info + countdown
        Text('4s inhale  ·  4s exhale',
            style: tt.bodySmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.40)
                    : Colors.black.withValues(alpha: 0.38))),
        const SizedBox(height: 4),
        Text('${secondsLeft}s remaining',
            style: tt.bodySmall?.copyWith(
                fontWeight: FontWeight.w700,
                color: isDark
                    ? Colors.white.withValues(alpha: 0.55)
                    : Colors.black.withValues(alpha: 0.45))),
        const SizedBox(height: 16),
        TextButton.icon(
          onPressed: onSkip,
          icon: const Icon(Icons.skip_next_rounded, size: 16),
          label: const Text('Skip to grounding'),
          style: TextButton.styleFrom(
              foregroundColor: AppColors.primary),
        ),
        const SizedBox(height: 20),
      ],
    );
  }

  static double _lerp(double a, double b, double t) => a + (b - a) * t;
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

  static const _items = _SosScreenState._groundingItems;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('STEP 2 — GROUND YOURSELF',
              textAlign: TextAlign.center,
              style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                  color: AppColors.mintDeep.withValues(alpha: 0.80))),
          const SizedBox(height: 4),
          Text(
            'Name each one slowly. Take your time.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.55)
                    : const Color(0xFF475467)),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.separated(
              itemCount: _items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) {
                final item = _items[i];
                return Container(
                  decoration: BoxDecoration(
                    color: item.color.withValues(alpha: isDark ? 0.10 : 0.06),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                        color: item.color.withValues(alpha: 0.25)),
                  ),
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 14),
                  child: Row(
                    children: [
                      // Number badge
                      Container(
                        width: 32, height: 32,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: item.color.withValues(alpha: 0.15),
                          border: Border.all(
                              color: item.color.withValues(alpha: 0.35)),
                        ),
                        child: Center(
                          child: Text('${5 - i}',
                              style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w900,
                                  color: item.color)),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Icon(item.icon, color: item.color, size: 18),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(item.label,
                            style: tt.bodyMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.85)
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
                style: TextStyle(fontWeight: FontWeight.w800)),
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
          Text('STEP 3 — LET IT SETTLE',
              style: TextStyle(
                  fontSize: 11, fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                  color: AppColors.violet.withValues(alpha: 0.80))),
          const SizedBox(height: 4),
          Text('A short calming audio is playing. Just listen.',
              textAlign: TextAlign.center,
              style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.55)
                      : const Color(0xFF475467))),
          const Spacer(),
          _PulsingAudioOrb(isPlaying: isPlaying),
          const SizedBox(height: 28),
          GlassCard(
            glowColor: AppColors.glowViolet,
            child: Column(
              children: [
                Text('Panic Calmer',
                    style: tt.titleLarge?.copyWith(
                        fontWeight: FontWeight.w900),
                    textAlign: TextAlign.center),
                const SizedBox(height: 6),
                Text(
                  'A short grounding audio for intense anxiety spikes.\nJust breathe and listen.',
                  style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.55)
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
                  isPlaying ? 'Playing…' : 'Paused',
                  style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.40)
                          : Colors.black.withValues(alpha: 0.35)),
                ),
              ],
            ),
          ),
          const Spacer(),
          FilledButton.icon(
            onPressed: onClose,
            icon: const Icon(Icons.check_rounded, size: 18),
            label: const Text('I feel better — close',
                style: TextStyle(fontWeight: FontWeight.w800)),
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
        vsync: this,
        duration: const Duration(milliseconds: 1800))
      ..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.88, end: 1.10)
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
          width: 140, height: 140,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [
              AppColors.violet.withValues(alpha: 0.55),
              AppColors.violet.withValues(alpha: 0.18),
              Colors.transparent,
            ], stops: const [0.0, 0.50, 1.0]),
            border: Border.all(
                color: AppColors.violet.withValues(alpha: 0.45), width: 2),
          ),
          child: Icon(
            widget.isPlaying
                ? Icons.music_note_rounded
                : Icons.music_off_rounded,
            color: AppColors.violet, size: 42,
          ),
        ),
      ),
    );
  }
}

// ── Step progress bar ─────────────────────────────────────────────────────────

class _StepBar extends StatelessWidget {
  final _SosStep current;
  const _StepBar({required this.current});

  @override
  Widget build(BuildContext context) {
    final colors = [AppColors.primary, AppColors.mintDeep, AppColors.violet];
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
                      : colors[i].withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 6),
        Row(
          children: List.generate(3, (i) {
            final isActive = i == active;
            return Expanded(
              child: Text(
                labels[i],
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: isActive ? FontWeight.w800 : FontWeight.w500,
                  color: isActive
                      ? colors[i]
                      : colors[i].withValues(alpha: 0.40),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}

// ── Arc painter for SOS orb ───────────────────────────────────────────────────

class _SosArcPainter extends CustomPainter {
  final double progress;
  final Color color;
  const _SosArcPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 5;
    final track = Paint()
      ..color = color.withValues(alpha: 0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, track);
    if (progress > 0) {
      final arc = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2,
        2 * math.pi * progress,
        false, arc,
      );
    }
  }

  @override
  bool shouldRepaint(_SosArcPainter old) =>
      old.progress != progress || old.color != color;
}
