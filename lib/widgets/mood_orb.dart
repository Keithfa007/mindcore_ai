import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'app_gradients.dart';

/// Animated ambient orb for the home screen.
/// Slowly breathes (scale) and rotates its inner shimmer.
/// Colour shifts based on [moodColor] — defaults to blue.
class MoodOrb extends StatefulWidget {
  final Color? moodColor;
  final double size;
  final Duration breathDuration;

  const MoodOrb({
    super.key,
    this.moodColor,
    this.size = 200,
    this.breathDuration = const Duration(seconds: 4),
  });

  @override
  State<MoodOrb> createState() => _MoodOrbState();
}

class _MoodOrbState extends State<MoodOrb> with TickerProviderStateMixin {
  late final AnimationController _breathCtrl;
  late final AnimationController _rotateCtrl;
  late final AnimationController _shimmerCtrl;

  late final Animation<double> _breathAnim;

  @override
  void initState() {
    super.initState();

    // Slow inhale/exhale
    _breathCtrl = AnimationController(
      vsync: this,
      duration: widget.breathDuration,
    )..repeat(reverse: true);

    _breathAnim = Tween<double>(begin: 0.92, end: 1.08).animate(
      CurvedAnimation(parent: _breathCtrl, curve: Curves.easeInOut),
    );

    // Slow inner shimmer rotation
    _rotateCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 12),
    )..repeat();

    // Shimmer opacity pulse
    _shimmerCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _breathCtrl.dispose();
    _rotateCtrl.dispose();
    _shimmerCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final baseColor = widget.moodColor ?? AppColors.primary;
    final accentColor = widget.moodColor == AppColors.mintDeep
        ? AppColors.primary
        : AppColors.mintDeep;

    return AnimatedBuilder(
      animation:
          Listenable.merge([_breathCtrl, _rotateCtrl, _shimmerCtrl]),
      builder: (context, _) {
        final scale = _breathAnim.value;
        final angle = _rotateCtrl.value * math.pi * 2;
        final shimmerAlpha = 0.15 + _shimmerCtrl.value * 0.25;

        return Transform.scale(
          scale: scale,
          child: SizedBox(
            width: widget.size,
            height: widget.size,
            child: Stack(
              alignment: Alignment.center,
              children: [
                // ── Outer glow ring ─────────────────────────────
                Container(
                  width: widget.size,
                  height: widget.size,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: baseColor.withValues(
                            alpha: isDark ? 0.35 : 0.20),
                        blurRadius: 60,
                        spreadRadius: 10,
                      ),
                      BoxShadow(
                        color: accentColor.withValues(
                            alpha: isDark ? 0.20 : 0.12),
                        blurRadius: 80,
                        spreadRadius: 5,
                      ),
                    ],
                  ),
                ),

                // ── Frosted orb body ────────────────────────────
                Container(
                  width: widget.size * 0.88,
                  height: widget.size * 0.88,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      center: const Alignment(-0.3, -0.4),
                      radius: 1.0,
                      colors: [
                        baseColor.withValues(
                            alpha: isDark ? 0.55 : 0.40),
                        accentColor.withValues(
                            alpha: isDark ? 0.35 : 0.25),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.55, 1.0],
                    ),
                    border: Border.all(
                      color: baseColor.withValues(
                          alpha: isDark ? 0.45 : 0.30),
                      width: 1.5,
                    ),
                  ),
                ),

                // ── Rotating inner shimmer ───────────────────────
                Transform.rotate(
                  angle: angle,
                  child: Container(
                    width: widget.size * 0.70,
                    height: widget.size * 0.70,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: SweepGradient(
                        colors: [
                          Colors.white.withValues(alpha: shimmerAlpha),
                          Colors.transparent,
                          Colors.white
                              .withValues(alpha: shimmerAlpha * 0.5),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.35, 0.65, 1.0],
                      ),
                    ),
                  ),
                ),

                // ── Centre highlight dot ────────────────────────
                Container(
                  width: widget.size * 0.18,
                  height: widget.size * 0.18,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        Colors.white.withValues(
                            alpha: isDark ? 0.85 : 0.70),
                        Colors.white.withValues(alpha: 0.0),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
