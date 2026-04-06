// lib/widgets/streak_badge.dart
//
// Animated streak counter with 3 visual states:
//  0       = dim grey pill
//  1–6     = glowing blue
//  7+      = pulsing neon violet (milestone achieved)

import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class StreakBadge extends StatefulWidget {
  final int streak;
  const StreakBadge({super.key, required this.streak});

  @override
  State<StreakBadge> createState() => _StreakBadgeState();
}

class _StreakBadgeState extends State<StreakBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl;
  late final Animation<double> _pulseAnim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    );
    _pulseAnim = Tween<double>(begin: 0.85, end: 1.0).animate(
      CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut),
    );
    if (widget.streak >= 7) _ctrl.repeat(reverse: true);
  }

  @override
  void didUpdateWidget(StreakBadge old) {
    super.didUpdateWidget(old);
    if (widget.streak >= 7 && !_ctrl.isAnimating) {
      _ctrl.repeat(reverse: true);
    } else if (widget.streak < 7 && _ctrl.isAnimating) {
      _ctrl.stop();
      _ctrl.value = 1.0;
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tt = Theme.of(context).textTheme;

    final s = widget.streak;
    final isEmpty = s == 0;
    final isMilestone = s >= 7;

    // Colour
    final Color accent = isEmpty
        ? (isDark
            ? Colors.white.withValues(alpha: 0.20)
            : Colors.black.withValues(alpha: 0.18))
        : isMilestone
            ? AppColors.violet
            : AppColors.primary;

    final Color glowColor = isEmpty
        ? Colors.transparent
        : isMilestone
            ? AppColors.violet.withValues(alpha: 0.35)
            : AppColors.primary.withValues(alpha: 0.28);

    // Label
    final String label = isEmpty
        ? 'Start your streak'
        : s == 1
            ? '1 day streak'
            : '$s day streak';

    final String emoji = isEmpty
        ? ''
        : isMilestone
            ? ' 🔥'
            : ' ✦';

    return AnimatedBuilder(
      animation: _ctrl,
      builder: (_, __) {
        final scale = isMilestone ? _pulseAnim.value : 1.0;
        return Transform.scale(
          scale: scale,
          child: Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: isDark ? 0.14 : 0.10),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: accent.withValues(alpha: isDark ? 0.45 : 0.35),
                width: isMilestone ? 1.5 : 1.0,
              ),
              boxShadow: isEmpty
                  ? null
                  : [
                      BoxShadow(
                        color: glowColor,
                        blurRadius: isMilestone ? 20 : 12,
                        spreadRadius: isMilestone ? 2 : 0,
                      ),
                    ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isEmpty
                      ? Icons.local_fire_department_outlined
                      : isMilestone
                          ? Icons.local_fire_department_rounded
                          : Icons.bolt_rounded,
                  size: 15,
                  color: accent,
                ),
                const SizedBox(width: 5),
                Text(
                  '$label$emoji',
                  style: tt.labelSmall?.copyWith(
                    color: isEmpty
                        ? (isDark
                            ? Colors.white.withValues(alpha: 0.40)
                            : Colors.black.withValues(alpha: 0.40))
                        : accent,
                    fontWeight: FontWeight.w800,
                    fontSize: 11,
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
