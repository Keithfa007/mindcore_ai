import 'dart:ui';
import 'package:flutter/material.dart';
import 'app_gradients.dart';

class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding,
    this.borderRadius = const BorderRadius.all(Radius.circular(20)),
    this.blur = 16,
    this.showBorder = true,
    this.showShadow = true,
  });

  final Widget child;
  final EdgeInsetsGeometry? padding;
  final BorderRadiusGeometry borderRadius;
  final double blur;
  final bool showBorder;
  final bool showShadow;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.08)
        : Colors.white.withValues(alpha: 0.40);

    final decoration = BoxDecoration(
      gradient: LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: isDark
            ? [
                Colors.white.withValues(alpha: 0.07),
                Colors.white.withValues(alpha: 0.03),
              ]
            : [
                Colors.white.withValues(alpha: 0.70),
                Colors.white.withValues(alpha: 0.40),
              ],
      ),
      borderRadius: borderRadius,
      border: showBorder ? Border.all(color: borderColor, width: 1.1) : null,
      boxShadow: showShadow
          ? [
              BoxShadow(
                color: isDark
                    ? Colors.black.withValues(alpha: 0.24)
                    : const Color(0x144D7CFF),
                blurRadius: 16,
                spreadRadius: 0,
                offset: const Offset(0, 8),
              ),
              BoxShadow(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.02)
                    : Colors.white.withValues(alpha: 0.40),
                blurRadius: 1,
                offset: const Offset(0, 1),
              ),
            ]
          : null,
    );

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blur, sigmaY: blur),
        child: Container(
          decoration: decoration,
          child: Stack(
            children: [
              Positioned.fill(
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: AppGradients.heroGlow(context),
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
