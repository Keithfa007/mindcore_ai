// lib/widgets/animated_logo.dart
//
// Animated brand logo for the login screen.
// Wraps the real logo512.png with:
//  - Slow breathing scale
//  - Rotating neon ring
//  - Pulsing outer glow
//  - Sweep shimmer

import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class AnimatedLogo extends StatefulWidget {
  final double size;
  const AnimatedLogo({super.key, this.size = 160});

  @override
  State<AnimatedLogo> createState() => _AnimatedLogoState();
}

class _AnimatedLogoState extends State<AnimatedLogo>
    with TickerProviderStateMixin {
  // Slow breathe
  late final AnimationController _breathCtrl;
  late final Animation<double> _breathAnim;

  // Rotating ring
  late final AnimationController _rotateCtrl;

  // Glow pulse
  late final AnimationController _glowCtrl;
  late final Animation<double> _glowAnim;

  @override
  void initState() {
    super.initState();

    _breathCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 3800),
    )..repeat(reverse: true);

    _breathAnim = Tween<double>(begin: 0.93, end: 1.06).animate(
      CurvedAnimation(parent: _breathCtrl, curve: Curves.easeInOut),
    );

    _rotateCtrl = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 10),
    )..repeat();

    _glowCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    )..repeat(reverse: true);

    _glowAnim = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _glowCtrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _breathCtrl.dispose();
    _rotateCtrl.dispose();
    _glowCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final s = widget.size;

    return AnimatedBuilder(
      animation: Listenable.merge([_breathCtrl, _rotateCtrl, _glowCtrl]),
      builder: (_, __) {
        final angle  = _rotateCtrl.value * math.pi * 2;
        final glow   = _glowAnim.value;
        final breath = _breathAnim.value;

        return Transform.scale(
          scale: breath,
          child: SizedBox(
            width: s,
            height: s,
            child: Stack(
              alignment: Alignment.center,
              children: [

                // ── Outer pulsing glow ───────────────────────────────────
                Container(
                  width: s,
                  height: s,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primary
                            .withValues(alpha: isDark ? 0.38 * glow : 0.22 * glow),
                        blurRadius: 55 * glow,
                        spreadRadius: 6 * glow,
                      ),
                      BoxShadow(
                        color: AppColors.mintDeep
                            .withValues(alpha: isDark ? 0.20 * glow : 0.12 * glow),
                        blurRadius: 70 * glow,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                ),

                // ── Rotating neon ring ───────────────────────────────────
                Transform.rotate(
                  angle: angle,
                  child: CustomPaint(
                    size: Size(s * 0.92, s * 0.92),
                    painter: _NeonRingPainter(
                      primaryColor: AppColors.primary,
                      accentColor: AppColors.mintDeep,
                      isDark: isDark,
                    ),
                  ),
                ),

                // ── Frosted circle behind logo ───────────────────────────
                Container(
                  width: s * 0.76,
                  height: s * 0.76,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        AppColors.primary.withValues(alpha: isDark ? 0.22 : 0.14),
                        AppColors.mintDeep.withValues(alpha: isDark ? 0.10 : 0.06),
                        Colors.transparent,
                      ],
                      stops: const [0.0, 0.55, 1.0],
                    ),
                  ),
                ),

                // ── Actual logo image ────────────────────────────────────
                ClipOval(
                  child: Image.asset(
                    'assets/images/logo512.png',
                    width: s * 0.58,
                    height: s * 0.58,
                    fit: BoxFit.contain,
                  ),
                ),

                // ── Sweep shimmer overlay ────────────────────────────────
                Transform.rotate(
                  angle: angle * 1.5,
                  child: Container(
                    width: s * 0.72,
                    height: s * 0.72,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: SweepGradient(
                        colors: [
                          Colors.white.withValues(alpha: 0.12),
                          Colors.transparent,
                          Colors.white.withValues(alpha: 0.06),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.30, 0.60, 1.0],
                      ),
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

// ── Custom painter for the dashed neon ring ───────────────────────────────

class _NeonRingPainter extends CustomPainter {
  final Color primaryColor;
  final Color accentColor;
  final bool isDark;

  const _NeonRingPainter({
    required this.primaryColor,
    required this.accentColor,
    required this.isDark,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width / 2;
    final cy = size.height / 2;
    final r  = (size.width / 2) - 2;

    // Gradient arc paint
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.0
      ..strokeCap = StrokeCap.round
      ..shader = SweepGradient(
        colors: [
          primaryColor.withValues(alpha: isDark ? 0.90 : 0.70),
          accentColor.withValues(alpha: isDark ? 0.70 : 0.50),
          primaryColor.withValues(alpha: 0.10),
          primaryColor.withValues(alpha: isDark ? 0.90 : 0.70),
        ],
        stops: const [0.0, 0.35, 0.65, 1.0],
      ).createShader(Rect.fromCircle(center: Offset(cx, cy), radius: r));

    canvas.drawCircle(Offset(cx, cy), r, paint);

    // Small accent dots at 0°, 90°, 180°, 270°
    final dotPaint = Paint()
      ..style = PaintingStyle.fill
      ..color = accentColor.withValues(alpha: isDark ? 0.85 : 0.65);

    for (int i = 0; i < 4; i++) {
      final angle = (i * math.pi / 2);
      final dx = cx + r * math.cos(angle);
      final dy = cy + r * math.sin(angle);
      canvas.drawCircle(Offset(dx, dy), 3.0, dotPaint);
    }
  }

  @override
  bool shouldRepaint(_NeonRingPainter old) =>
      old.isDark != isDark ||
      old.primaryColor != primaryColor ||
      old.accentColor != accentColor;
}
