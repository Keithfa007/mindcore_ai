// lib/pages/sos_screen.dart
//
// SOS Mode — one-tap grounding sequence.
// Step 1: 60-second box breathing
// Step 2: 5-4-3-2-1 grounding technique
// Step 3: Auto-play calming audio

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

enum _SosStep { breathe, grounding, audio }

// Simple data class — avoids Dart 3 record syntax
class _GroundingItem {
  final String label;
  final IconData icon;
  const _GroundingItem(this.label, this.icon);
}

class SosScreen extends StatefulWidget {
  const SosScreen({super.key});
  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> with TickerProviderStateMixin {
  _SosStep _step = _SosStep.breathe;

  // Breathing
  late final AnimationController _breathCtrl;
  late final Animation<double> _breathAnim;
  Timer? _breathTimer;
  int _breathSecondsLeft = 60;
  String _breathPhaseLabel = 'Breathe in';

  // Audio
  final AudioPlayer _player = AudioPlayer();
  bool _audioPlaying = false;

  static const _groundingItems = [
    _GroundingItem('5 things you can see',  Icons.visibility_rounded),
    _GroundingItem('4 things you can touch', Icons.touch_app_rounded),
    _GroundingItem('3 things you can hear',  Icons.hearing_rounded),
    _GroundingItem('2 things you can smell', Icons.air_rounded),
    _GroundingItem('1 thing you can taste',  Icons.restaurant_rounded),
  ];

  @override
  void initState() {
    super.initState();

    // 8s breath cycle — first half inhale, second half exhale
    _breathCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    _breathAnim = Tween<double>(begin: 0.7, end: 1.15).animate(
      CurvedAnimation(parent: _breathCtrl, curve: Curves.easeInOut),
    );

    _breathCtrl.addListener(() {
      final phase = _breathCtrl.value < 0.5 ? 'Breathe in' : 'Breathe out';
      if (phase != _breathPhaseLabel && mounted) {
        setState(() => _breathPhaseLabel = phase);
      }
    });

    // 60s countdown then auto-advance
    _breathTimer = Timer.periodic(const Duration(seconds: 1), (_) {
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

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header
                Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.close,
                          color: isDark ? Colors.white54 : Colors.black45),
                      onPressed: () {
                        _stopAudio();
                        Navigator.of(context).pop();
                      },
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'SOS \u2014 Grounding Mode',
                      style: tt.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: isDark ? Colors.white : const Color(0xFF0E1320),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 12),
                _StepIndicator(current: _step),
                const SizedBox(height: 28),

                Expanded(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 600),
                    child: _buildStepContent(tt, isDark),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStepContent(TextTheme tt, bool isDark) {
    switch (_step) {
      case _SosStep.breathe:
        return _buildBreatheStep(tt, isDark);
      case _SosStep.grounding:
        return _buildGroundingStep(tt, isDark);
      case _SosStep.audio:
        return _buildAudioStep(tt, isDark);
    }
  }

  // ── Step 1: Breathing ─────────────────────────────────────────────
  Widget _buildBreatheStep(TextTheme tt, bool isDark) {
    return Column(
      key: const ValueKey('breathe'),
      children: [
        Text(
          'Step 1 of 3 \u2014 Breathe',
          style: tt.labelSmall?.copyWith(
            color: AppColors.primary,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'Follow the orb. Slow, steady breaths.',
          style: tt.bodyMedium?.copyWith(
            color: isDark
                ? Colors.white.withValues(alpha: 0.60)
                : const Color(0xFF475467),
          ),
          textAlign: TextAlign.center,
        ),
        const Spacer(),

        AnimatedBuilder(
          animation: _breathAnim,
          builder: (_, __) => Transform.scale(
            scale: _breathAnim.value,
            child: Container(
              width: 180,
              height: 180,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    AppColors.primary.withValues(alpha: 0.55),
                    AppColors.mintDeep.withValues(alpha: 0.25),
                    Colors.transparent,
                  ],
                  stops: const [0.0, 0.55, 1.0],
                ),
                border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.50), width: 2),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.30),
                    blurRadius: 50,
                    spreadRadius: 8,
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 24),

        AnimatedSwitcher(
          duration: const Duration(milliseconds: 400),
          child: Text(
            _breathPhaseLabel,
            key: ValueKey(_breathPhaseLabel),
            style: tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
              letterSpacing: -0.5,
            ),
          ),
        ),
        const SizedBox(height: 10),

        Text(
          '${_breathSecondsLeft}s remaining',
          style: tt.bodySmall?.copyWith(
            color: isDark
                ? Colors.white.withValues(alpha: 0.40)
                : Colors.black.withValues(alpha: 0.40),
          ),
        ),
        const Spacer(),

        TextButton(
          onPressed: _advanceStep,
          child: Text(
            'Skip breathing \u2192',
            style: tt.labelSmall?.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        const SizedBox(height: 8),
      ],
    );
  }

  // ── Step 2: 5-4-3-2-1 grounding ──────────────────────────────────
  Widget _buildGroundingStep(TextTheme tt, bool isDark) {
    return Column(
      key: const ValueKey('grounding'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          'Step 2 of 3 \u2014 Ground yourself',
          style: tt.labelSmall?.copyWith(
            color: AppColors.mintDeep,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 6),
        Text(
          'The 5-4-3-2-1 technique. Take your time.',
          style: tt.bodyMedium?.copyWith(
            color: isDark
                ? Colors.white.withValues(alpha: 0.60)
                : const Color(0xFF475467),
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 20),

        // Grounding items — uses _GroundingItem class, no records
        for (final item in _groundingItems) ...[
          GlassCard(
            glowColor: AppColors.glowMint,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              children: [
                Icon(item.icon, color: AppColors.mintDeep, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    item.label,
                    style: tt.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
        ],

        const Spacer(),
        FilledButton(
          onPressed: _advanceStep,
          style: FilledButton.styleFrom(
            backgroundColor: AppColors.mintDeep,
            minimumSize: const Size.fromHeight(52),
          ),
          child: const Text("I'm ready \u2192 Play calming audio"),
        ),
        const SizedBox(height: 8),
      ],
    );
  }

  // ── Step 3: Calming audio ─────────────────────────────────────────
  Widget _buildAudioStep(TextTheme tt, bool isDark) {
    return Column(
      key: const ValueKey('audio'),
      children: [
        Text(
          'Step 3 of 3 \u2014 Let it settle',
          style: tt.labelSmall?.copyWith(
            color: AppColors.violet,
            fontWeight: FontWeight.w800,
            letterSpacing: 0.5,
          ),
        ),
        const SizedBox(height: 6),
        Text(
          'A short calming audio is playing. Just listen.',
          style: tt.bodyMedium?.copyWith(
            color: isDark
                ? Colors.white.withValues(alpha: 0.60)
                : const Color(0xFF475467),
          ),
          textAlign: TextAlign.center,
        ),
        const Spacer(),

        _AudioOrb(isPlaying: _audioPlaying),
        const SizedBox(height: 28),

        GlassCard(
          glowColor: AppColors.glowViolet,
          padding: const EdgeInsets.all(18),
          child: Column(
            children: [
              Text(
                'Panic Calmer',
                style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 6),
              Text(
                'Short grounding audio for intense anxiety spikes.',
                style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.55)
                      : const Color(0xFF475467),
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 14),
              IconButton.filled(
                onPressed: _audioPlaying ? _stopAudio : _startAudio,
                style:
                    IconButton.styleFrom(backgroundColor: AppColors.violet),
                icon: Icon(
                  _audioPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
                  color: Colors.white,
                ),
              ),
            ],
          ),
        ),
        const Spacer(),

        FilledButton(
          onPressed: () {
            _stopAudio();
            Navigator.of(context).pop();
          },
          style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52)),
          child: const Text('I feel better \u2014 close'),
        ),
        const SizedBox(height: 8),
      ],
    );
  }
}

// ── Step progress bar ─────────────────────────────────────────────────

class _StepIndicator extends StatelessWidget {
  final _SosStep current;
  const _StepIndicator({required this.current});

  @override
  Widget build(BuildContext context) {
    final colors = [AppColors.primary, AppColors.mintDeep, AppColors.violet];
    final steps  = [_SosStep.breathe, _SosStep.grounding, _SosStep.audio];
    final active = steps.indexOf(current);

    return Row(
      children: List.generate(3, (i) {
        return Expanded(
          child: Container(
            margin: EdgeInsets.only(right: i < 2 ? 6 : 0),
            height: 4,
            decoration: BoxDecoration(
              color: i <= active
                  ? colors[i]
                  : colors[i].withValues(alpha: 0.20),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}

// ── Pulsing audio orb ─────────────────────────────────────────────────

class _AudioOrb extends StatefulWidget {
  final bool isPlaying;
  const _AudioOrb({required this.isPlaying});
  @override
  State<_AudioOrb> createState() => _AudioOrbState();
}

class _AudioOrbState extends State<_AudioOrb>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 2000))
      ..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.88, end: 1.08).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
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
      builder: (_, __) => Transform.scale(
        scale: widget.isPlaying ? _anim.value : 1.0,
        child: Container(
          width: 130,
          height: 130,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(
              colors: [
                AppColors.violet.withValues(alpha: 0.50),
                AppColors.violetDeep.withValues(alpha: 0.20),
                Colors.transparent,
              ],
              stops: const [0.0, 0.55, 1.0],
            ),
            border: Border.all(
                color: AppColors.violet.withValues(alpha: 0.50), width: 2),
            boxShadow: [
              BoxShadow(
                color: AppColors.violet.withValues(
                    alpha: widget.isPlaying ? 0.35 : 0.15),
                blurRadius: 40,
                spreadRadius: 4,
              ),
            ],
          ),
          child: Icon(
            widget.isPlaying
                ? Icons.music_note_rounded
                : Icons.music_off_rounded,
            color: AppColors.violet,
            size: 40,
          ),
        ),
      ),
    );
  }
}
