import 'package:flutter/material.dart';

import 'package:mindcore_ai/services/settings_service.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

class PrivacyControlsScreen extends StatelessWidget {
  const PrivacyControlsScreen({super.key});

  Future<void> _confirmClear(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear local data?'),
        content: const Text(
          'This removes local journal/history and today caches for tips & affirmations.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );

    if (ok != true) return;

    await SettingsService.clearLocalData();

    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Local data cleared')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PageScaffold(
      appBar: const AppTopBar(title: 'Privacy & Controls'),
      body: AnimatedBackdrop(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          child: GlassCard(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
              children: [
                const SectionHeroCard(
                  title: 'Privacy first',
                  subtitle: 'MindReset AI is designed to feel calm, private, and in your control.',
                ),
                const SizedBox(height: 14),

                _InfoCard(
                  title: 'Local storage',
                  body:
                  'Your journal entries, mood history, and daily caches are stored locally on your device. '
                      'You can clear them anytime.',
                ),
                const SizedBox(height: 12),

                _InfoCard(
                  title: 'Export (coming soon)',
                  body:
                  'We’ll add export options (CSV/JSON) in a future update. '
                      'For now, you can clear local data anytime.',
                ),
                const SizedBox(height: 18),

                SizedBox(
                  width: double.infinity,
                  child: FilledButton.tonal(
                    onPressed: () => _confirmClear(context),
                    child: const Text('Clear local data'),
                  ),
                ),
                const SizedBox(height: 10),

                Text(
                  'Clearing local data removes journal/history and daily caches on this device. '
                      'It does not affect any cloud data.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.65),
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
