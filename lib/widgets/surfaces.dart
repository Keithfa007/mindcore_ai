import 'package:flutter/material.dart';
import 'app_gradients.dart';
import 'premium_motion.dart';

const double _rLg = 20;
const double _rInner = 16;
const List<Color> _primaryButton = [Color(0xFF4D7CFF), Color(0xFF74C3FF)];
const List<Color> _mintButton = [Color(0xFF32D0BE), Color(0xFF89E0CF)];

class SurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final EdgeInsets? margin;
  final Color? color;

  const SurfaceCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;
    final bg = color ?? (isDark ? const Color(0xFF121A27) : Colors.white.withValues(alpha: 0.76));
    final borderColor = isDark
        ? Colors.white.withValues(alpha: 0.08)
        : Colors.white.withValues(alpha: 0.60);

    return Container(
      margin: margin ?? const EdgeInsets.symmetric(vertical: 5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(_rLg),
        border: Border.all(color: borderColor),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.28)
                : const Color(0x144D7CFF),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(14),
        child: child,
      ),
    );
  }
}

class NestCard extends StatelessWidget {
  final Widget child;
  final EdgeInsets? padding;
  final Color? color;

  const NestCard({
    super.key,
    required this.child,
    this.padding,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final surface = color ?? (isDark ? const Color(0xFF111A28) : Colors.white.withValues(alpha: 0.86));
    return Container(
      decoration: BoxDecoration(
        color: surface,
        borderRadius: BorderRadius.circular(_rInner),
        border: Border.all(
          color: isDark
              ? Colors.white.withValues(alpha: 0.08)
              : Colors.white.withValues(alpha: 0.70),
        ),
        boxShadow: [
          BoxShadow(
            color: isDark
                ? Colors.black.withValues(alpha: 0.22)
                : const Color(0x0E4D7CFF),
            blurRadius: 16,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.fromLTRB(13, 11, 13, 13),
        child: child,
      ),
    );
  }
}

class GradientButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final List<Color> colors;
  final EdgeInsets padding;
  final BorderRadius borderRadius;
  final Widget? leading;

  const GradientButton({
    super.key,
    required this.label,
    this.onPressed,
    this.colors = _primaryButton,
    this.padding = const EdgeInsets.symmetric(vertical: 13),
    this.borderRadius = const BorderRadius.all(Radius.circular(18)),
    this.leading,
  });

  factory GradientButton.primary(String label, {Key? key, VoidCallback? onPressed, Widget? leading}) =>
      GradientButton(
        key: key,
        label: label,
        onPressed: onPressed,
        colors: _primaryButton,
        padding: const EdgeInsets.symmetric(vertical: 13),
        leading: leading,
      );

  factory GradientButton.mint(String label, {Key? key, VoidCallback? onPressed, Widget? leading}) =>
      GradientButton(
        key: key,
        label: label,
        onPressed: onPressed,
        colors: _mintButton,
        leading: leading,
      );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return PressScale(
      onTap: onPressed,
      borderRadius: borderRadius,
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: colors),
          borderRadius: borderRadius,
          border: Border.all(color: Colors.white.withValues(alpha: isDark ? 0.10 : 0.30)),
          boxShadow: [
            BoxShadow(
              color: colors.first.withValues(alpha: isDark ? 0.26 : 0.24),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: borderRadius,
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Colors.white.withValues(alpha: 0.14),
                Colors.transparent,
              ],
            ),
          ),
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: 16).add(padding),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (leading != null) ...[
                  leading!,
                  const SizedBox(width: 10),
                ],
                Flexible(
                  child: Text(
                    label,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          letterSpacing: -0.05,
                        ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
