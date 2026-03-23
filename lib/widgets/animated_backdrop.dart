import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'app_gradients.dart';

/// Global immersive backdrop used across the app.
/// Keeps the wellness feel, but adds a subtle premium AI glow.
class AnimatedBackdrop extends StatefulWidget {
  final Widget child;
  final Duration? duration;

  const AnimatedBackdrop({
    super.key,
    required this.child,
    this.duration,
  });

  @override
  State<AnimatedBackdrop> createState() => _AnimatedBackdropState();
}

class _AnimatedBackdropState extends State<AnimatedBackdrop>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
      vsync: this,
      duration: widget.duration ?? const Duration(seconds: 18),
    )..repeat();
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final baseGradient = AppGradients.body(context);
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Stack(
      children: [
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(gradient: baseGradient),
          ),
        ),
        Positioned.fill(
          child: AnimatedBuilder(
            animation: _c,
            builder: (context, _) {
              final t = _c.value;
              final x1 = -0.8 + (math.sin(t * math.pi * 2) * 0.22);
              final y1 = -0.95 + (math.cos(t * math.pi * 2) * 0.14);
              final x2 = 0.75 + (math.cos(t * math.pi * 2) * 0.18);
              final y2 = -0.25 + (math.sin(t * math.pi * 2) * 0.20);
              final x3 = -0.15 + (math.sin(t * math.pi * 4) * 0.10);
              final y3 = 0.90 + (math.cos(t * math.pi * 2) * 0.08);

              return Stack(
                children: [
                  _GlowBlob(
                    alignment: Alignment(x1, y1),
                    radius: 0.85,
                    color: isDark
                        ? AppColors.glowMint.withValues(alpha: 0.20)
                        : Colors.white.withValues(alpha: 0.30),
                  ),
                  _GlowBlob(
                    alignment: Alignment(x2, y2),
                    radius: 0.95,
                    color: isDark
                        ? AppColors.glowBlue.withValues(alpha: 0.22)
                        : AppColors.glowBlue.withValues(alpha: 0.14),
                  ),
                  _GlowBlob(
                    alignment: Alignment(x3, y3),
                    radius: 1.1,
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.05)
                        : AppColors.glowMint.withValues(alpha: 0.10),
                  ),
                ],
              );
            },
          ),
        ),
        Positioned.fill(child: widget.child),
      ],
    );
  }
}

class _GlowBlob extends StatelessWidget {
  final Alignment alignment;
  final double radius;
  final Color color;

  const _GlowBlob({
    required this.alignment,
    required this.radius,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: RadialGradient(
          center: alignment,
          radius: radius,
          colors: [color, Colors.transparent],
          stops: const [0.0, 1.0],
        ),
      ),
    );
  }
}
