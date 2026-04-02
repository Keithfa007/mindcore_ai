import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'app_gradients.dart';

/// Aurora-style animated backdrop used across the app.
/// Five independently drifting glow blobs create a living,
/// futuristic atmosphere without hurting performance.
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
      duration: widget.duration ?? const Duration(seconds: 22),
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
        // ── Base gradient ─────────────────────────────────────────
        Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(gradient: baseGradient),
          ),
        ),

        // ── Animated aurora blobs ─────────────────────────────────
        Positioned.fill(
          child: AnimatedBuilder(
            animation: _c,
            builder: (context, _) {
              final t = _c.value;

              // Each blob has its own phase offset for organic movement
              final x1 = -0.7 + math.sin(t * math.pi * 2.0) * 0.28;
              final y1 = -1.0 + math.cos(t * math.pi * 1.6) * 0.18;

              final x2 = 0.80 + math.cos(t * math.pi * 1.8) * 0.22;
              final y2 = -0.20 + math.sin(t * math.pi * 2.2) * 0.24;

              final x3 = -0.10 + math.sin(t * math.pi * 3.0 + 1.0) * 0.14;
              final y3 = 0.85 + math.cos(t * math.pi * 1.4) * 0.12;

              final x4 = 0.30 + math.cos(t * math.pi * 2.5 + 0.5) * 0.20;
              final y4 = 0.40 + math.sin(t * math.pi * 1.9 + 1.2) * 0.18;

              final x5 = -0.60 + math.sin(t * math.pi * 1.3 + 2.0) * 0.16;
              final y5 = 0.20 + math.cos(t * math.pi * 2.7) * 0.22;

              return Stack(
                children: [
                  // Blob 1 — teal top-left
                  _AuroraBlob(
                    alignment: Alignment(x1, y1),
                    radius: 0.90,
                    color: isDark
                        ? AppColors.glowMint.withValues(alpha: 0.28)
                        : Colors.white.withValues(alpha: 0.34),
                  ),
                  // Blob 2 — blue right
                  _AuroraBlob(
                    alignment: Alignment(x2, y2),
                    radius: 1.00,
                    color: isDark
                        ? AppColors.glowBlue.withValues(alpha: 0.32)
                        : AppColors.glowBlue.withValues(alpha: 0.18),
                  ),
                  // Blob 3 — subtle white bottom
                  _AuroraBlob(
                    alignment: Alignment(x3, y3),
                    radius: 1.15,
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.04)
                        : AppColors.glowMint.withValues(alpha: 0.14),
                  ),
                  // Blob 4 — violet mid (dark only)
                  if (isDark)
                    _AuroraBlob(
                      alignment: Alignment(x4, y4),
                      radius: 0.75,
                      color: AppColors.glowViolet.withValues(alpha: 0.20),
                    ),
                  // Blob 5 — teal secondary drift
                  _AuroraBlob(
                    alignment: Alignment(x5, y5),
                    radius: 0.80,
                    color: isDark
                        ? AppColors.glowMint.withValues(alpha: 0.14)
                        : AppColors.glowBlue.withValues(alpha: 0.10),
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

class _AuroraBlob extends StatelessWidget {
  final Alignment alignment;
  final double radius;
  final Color color;

  const _AuroraBlob({
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
