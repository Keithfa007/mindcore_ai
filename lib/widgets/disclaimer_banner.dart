// lib/widgets/disclaimer_banner.dart
//
// Slim persistent disclaimer banner for the chat screen.
// Always visible, non-dismissible, non-intrusive.

import 'package:flutter/material.dart';

class DisclaimerBanner extends StatelessWidget {
  const DisclaimerBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: () => Navigator.of(context).pushNamed('/disclaimer'),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: cs.primary.withValues(alpha: isDark ? 0.08 : 0.06),
          border: Border(
            bottom: BorderSide(
              color: cs.primary.withValues(alpha: isDark ? 0.15 : 0.10),
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.info_outline_rounded,
              size: 13,
              color: cs.primary.withValues(alpha: 0.70),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: Text(
                'MindCore AI is not a substitute for professional mental health support.',
                style: tt.bodySmall?.copyWith(
                  fontSize: 11,
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.45),
                  height: 1.3,
                ),
              ),
            ),
            const SizedBox(width: 6),
            Text(
              'Learn more',
              style: tt.labelSmall?.copyWith(
                fontSize: 11,
                color: cs.primary.withValues(alpha: 0.70),
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
