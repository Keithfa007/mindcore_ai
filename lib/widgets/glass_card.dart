import 'dart:ui';
import 'package:flutter/material.dart';
import 'app_gradients.dart';

/// Deep glassmorphism card with:
/// - Real backdrop blur
/// - Neon glow border option
/// - Layered hero shimmer
/// - Subtle inner highlight
class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius = const BorderRadius.all(Radius.circular(22)),
    this.blur = 20,
    this.showBorder = true,
    this.showShadow = true,
    this.glowColor,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final BorderRadiusGeometry borderRadius;
  final double blur;
  final bool showBorder;
  final bool showShadow;

  /// Optional neon glow colour — pass e.g. AppColors.glowMint
  final Color? glowColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Border: neon tint if glowColor supplied, else standard glass border
    final borderColor = glowColor != null
        ? glowColor!.withValues(alpha: isDark ? 0.55 : 0.40)
        : (isDark
            ? Colors.white.withValues(alpha: 0.09)
            : Colors.white.withValues(alpha: 0.45));

    final fillColors = isDark
        ? [
            Colors.white.withValues(alpha: 0.07),
            Colors.white.withValues(alpha: 0.03),
          ]
        : [
            Colors.white.withValues(alpha: 0.72),
            Colors.white.withValues(alpha: 0.42),
          ];

    final shadows = showShadow
        ? [
            BoxShadow(
              color: glowColor != null
                  ? glowColor!.withValues(alpha: isDark ? 0.28 : 0.14)
                  : (isDark
                      ? Colors.black.withValues(alpha: 0.36)
                      : const Color(0x1A4D7CFF)),
              blurRadius: isDark ? 24 : 18,
              spreadRadius: glowColor != null ? 2 : 0,
              offset: const Offset(0, 8),
            ),
            // Inner top highlight
            BoxShadow(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.03)
                  : Colors.white.withValues(alpha: 0.50),
              blurRadius: 1,
              offset: const Offset(0, 1),
            ),
          ]
        : null;

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: fillColors,
            ),
            borderRadius: borderRadius,
            border: showBorder
                ? Border.all(color: borderColor, width: 1.2)
                : null,
            boxShadow: shadows,
          ),
          child: Stack(
            children: [
              // Hero shimmer overlay
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: AppGradients.heroGlow(context),
                    ),
                  ),
                ),
              ),
              // Inner top-edge highlight
              Positioned(
                top: 0,
                left: 0,
                right: 0,
                height: 1,
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          Colors.white.withValues(
                              alpha: isDark ? 0.10 : 0.60),
                          Colors.transparent,
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: padding ?? const EdgeInsets.all(16),
                child: child,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
