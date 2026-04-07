// lib/widgets/mood_prediction_chip.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/ai/mood_pattern_service.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';

/// Glassmorphism insight card shown when a genuine mood pattern is detected.
class MoodPredictionChip extends StatelessWidget {
  final MoodPrediction prediction;
  final VoidCallback? onAction;

  const MoodPredictionChip({
    super.key,
    required this.prediction,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final accent = prediction.accentColor;

    return GlassCard(
      glowColor: accent.withValues(alpha: 0.35),
      padding: const EdgeInsets.all(16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Icon bubble
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: accent.withValues(alpha: isDark ? 0.18 : 0.12),
              border: Border.all(
                color: accent.withValues(alpha: isDark ? 0.40 : 0.25),
              ),
            ),
            child: Icon(prediction.icon, color: accent, size: 20),
          ),
          const SizedBox(width: 14),

          // Text + optional CTA
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Headline + badge
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        prediction.headline,
                        style: tt.titleSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: isDark
                              ? Colors.white
                              : const Color(0xFF0E1320),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: accent.withValues(
                            alpha: isDark ? 0.20 : 0.12),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        'Insight',
                        style: tt.labelSmall?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w800,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                // Detail
                Text(
                  prediction.detail,
                  style: tt.bodySmall?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.62)
                        : const Color(0xFF475467),
                    height: 1.5,
                  ),
                ),

                // Action link
                if (prediction.actionLabel != null &&
                    onAction != null) ...[
                  const SizedBox(height: 10),
                  GestureDetector(
                    onTap: onAction,
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          prediction.actionLabel!,
                          style: tt.labelSmall?.copyWith(
                            color: accent,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(Icons.arrow_forward_rounded,
                            size: 13, color: accent),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
