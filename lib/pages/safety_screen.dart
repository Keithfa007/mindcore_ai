import 'package:flutter/material.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

class SafetyScreen extends StatelessWidget {
  const SafetyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PageScaffold(
      appBar: const AppTopBar(title: 'Safety'),
      body: AnimatedBackdrop(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          child: GlassCard(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
              children: [
                const SectionHeroCard(
                  title: 'You’re not alone',
                  subtitle: 'If you’re in danger or feel you might act, get real-world support now.',
                ),
                const SizedBox(height: 14),

                _InfoCard(
                  title: 'Important',
                  body:
                  'MindCore AI is for wellbeing support and self-care. '
                      'It is not a crisis service and cannot provide emergency help.',
                ),
                const SizedBox(height: 12),

                _InfoCard(
                  title: 'If you are in immediate danger',
                  body: 'Call your local emergency number now.',
                ),
                const SizedBox(height: 12),

                // Malta-friendly defaults (fits you + most of your first users)
                _InfoCard(
                  title: 'If you are in Malta',
                  body:
                  '• Emergency: 112\n'
                      '• Supportline: 179\n\n'


                ),
                const SizedBox(height: 12),

                _InfoCard(
                  title: 'If you are in Europe',
                  body:
                  '• Emergency: 112\n'
                      'If you are outside Europe, check with your local emergency services.',

                ),
                const SizedBox(height: 12),

                _InfoCard(
                  title: 'A simple next step',
                  body:
                  'If you can, reach out to someone you trust and stay with them. '
                      'You deserve support.',
                ),
                const SizedBox(height: 18),

                Text(
                  'If you’d like, you can also use a Quick Reset now.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.75),
                  ),
                ),
                const SizedBox(height: 10),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: () => Navigator.of(context).pushNamed('/reset'),
                    child: const Text('Start Quick Reset'),
                  ),
                ),

                const SizedBox(height: 10),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  final String title;
  final String body;

  const _InfoCard({required this.title, required this.body});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.8)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Text(body, style: theme.textTheme.bodyMedium),
        ],
      ),
    );
  }
}
