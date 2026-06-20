// lib/pages/privacy_controls_screen.dart
//
// Privacy & Transparency screen — comprehensive view of data practices.
// Accessible from Settings → Trust & Safety and from onboarding.

import 'package:flutter/material.dart';

import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class PrivacyControlsScreen extends StatelessWidget {
  const PrivacyControlsScreen({super.key});

  Future<void> _confirmClear(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear local data?'),
        content: const Text(
          'This removes local journal, chat history, and daily caches '
          'on this device. Cloud data is unaffected.',
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
    final theme  = Theme.of(context);
    final tt     = theme.textTheme;
    final isDark = theme.brightness == Brightness.dark;

    final subtleColor = isDark
        ? Colors.white.withValues(alpha: 0.50)
        : const Color(0xFF475467);

    return PageScaffold(
      appBar: const AppTopBar(title: 'Privacy & Transparency'),
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
          children: [
            // ── Hero ──────────────────────────────────────────────
            GlassCard(
              glowColor: AppColors.primary.withValues(alpha: 0.15),
              padding: const EdgeInsets.all(22),
              child: Column(
                children: [
                  Container(
                    width: 56, height: 56,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppColors.primary.withValues(alpha: 0.12),
                      border: Border.all(
                        color: AppColors.primary.withValues(alpha: 0.30),
                      ),
                    ),
                    child: Icon(Icons.shield_rounded,
                        color: AppColors.primary, size: 28),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Your privacy is not a feature.\nIt\u2019s a promise.',
                    textAlign: TextAlign.center,
                    style: tt.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900,
                      letterSpacing: -0.5,
                      height: 1.3,
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'MindCore AI was built by someone who needed a safe space. '
                    'That\u2019s what this is \u2014 a space you can trust completely.',
                    textAlign: TextAlign.center,
                    style: tt.bodySmall?.copyWith(
                      color: subtleColor,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── Section 1: Your Data ──────────────────────────────
            _SectionHeader(
              icon: Icons.lock_rounded,
              color: AppColors.primary,
              label: 'Your Data Stays Yours',
            ),
            const SizedBox(height: 8),
            _PromiseCard(
              icon: Icons.chat_bubble_outline_rounded,
              color: AppColors.primary,
              title: 'Conversations',
              body: 'Your chat history is stored locally on your device. '
                  'It never leaves your phone unless you choose to export it.',
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),
            _PromiseCard(
              icon: Icons.mood_rounded,
              color: AppColors.mintDeep,
              title: 'Mood & journal data',
              body: 'Your mood logs and journal entries are stored securely in '
                  'Firebase under your personal account. Only you can read or write '
                  'your own data \u2014 enforced at the database level.',
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),
            _PromiseCard(
              icon: Icons.login_rounded,
              color: AppColors.violet,
              title: 'Authentication',
              body: 'MindCore AI uses Google Sign-In. We never see, store, or '
                  'handle your password. Authentication is managed entirely by Google.',
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 24),

            // ── Section 2: How AI Works ───────────────────────────
            _SectionHeader(
              icon: Icons.psychology_rounded,
              color: AppColors.mintDeep,
              label: 'How the AI Works',
            ),
            const SizedBox(height: 8),
            _PromiseCard(
              icon: Icons.smart_toy_outlined,
              color: AppColors.mintDeep,
              title: 'AI processing',
              body: 'Your messages are sent to OpenAI\u2019s API to generate responses. '
                  'OpenAI does not use API data to train their models. '
                  'Your conversations are not stored on OpenAI\u2019s servers beyond '
                  'the time needed to process each message.',
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),
            _PromiseCard(
              icon: Icons.memory_rounded,
              color: AppColors.primary,
              title: 'No AI training on your data',
              body: 'Nothing you say in MindCore AI is ever used to train, '
                  'fine-tune, or improve any AI model. Your words are yours alone.',
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 24),

            // ── Section 3: What We Store ──────────────────────────
            _SectionHeader(
              icon: Icons.storage_rounded,
              color: AppColors.violet,
              label: 'What We Store & Where',
            ),
            const SizedBox(height: 8),
            GlassCard(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _StorageRow(
                    label: 'Chat history',
                    location: 'Your device only',
                    icon: Icons.phone_android_rounded,
                    isDark: isDark, tt: tt,
                  ),
                  _StorageDivider(isDark: isDark),
                  _StorageRow(
                    label: 'Mood logs',
                    location: 'Firebase (your account)',
                    icon: Icons.cloud_outlined,
                    isDark: isDark, tt: tt,
                  ),
                  _StorageDivider(isDark: isDark),
                  _StorageRow(
                    label: 'Journal entries',
                    location: 'Firebase (your account)',
                    icon: Icons.cloud_outlined,
                    isDark: isDark, tt: tt,
                  ),
                  _StorageDivider(isDark: isDark),
                  _StorageRow(
                    label: 'Preferences & settings',
                    location: 'Your device only',
                    icon: Icons.phone_android_rounded,
                    isDark: isDark, tt: tt,
                  ),
                  _StorageDivider(isDark: isDark),
                  _StorageRow(
                    label: 'Voice recordings',
                    location: 'Never stored',
                    icon: Icons.delete_forever_rounded,
                    isDark: isDark, tt: tt,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // ── Section 4: What We Never Do ───────────────────────
            _SectionHeader(
              icon: Icons.block_rounded,
              color: const Color(0xFFE24B4A),
              label: 'What We Never Do',
            ),
            const SizedBox(height: 8),
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                children: [
                  _NeverRow(text: 'Sell your data to anyone', isDark: isDark, tt: tt),
                  _NeverRow(text: 'Show you advertisements', isDark: isDark, tt: tt),
                  _NeverRow(text: 'Share data with third-party marketers', isDark: isDark, tt: tt),
                  _NeverRow(text: 'Use your conversations to train AI', isDark: isDark, tt: tt),
                  _NeverRow(text: 'Track you across apps or websites', isDark: isDark, tt: tt),
                  _NeverRow(text: 'Store your voice recordings', isDark: isDark, tt: tt, last: true),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // ── Section 5: Your Controls ──────────────────────────
            _SectionHeader(
              icon: Icons.tune_rounded,
              color: const Color(0xFF888780),
              label: 'Your Controls',
            ),
            const SizedBox(height: 8),
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'You can clear all local data at any time. This removes chat history, '
                    'journal caches, and daily content from your device.',
                    style: tt.bodyMedium?.copyWith(
                      color: subtleColor,
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.tonal(
                      onPressed: () => _confirmClear(context),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(46),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                      ),
                      child: const Text('Clear local data'),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'PDF journal export is available from the Daily Hub. '
                    'Additional export options (CSV/JSON) coming in a future update.',
                    style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.35)
                          : Colors.black.withValues(alpha: 0.35),
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

// ── Helper widgets ──────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String label;
  const _SectionHeader({
    required this.icon, required this.color, required this.label,
  });
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 2),
      child: Row(children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 6),
        Text(
          label.toUpperCase(),
          style: TextStyle(
            fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.8,
            color: isDark
                ? Colors.white.withValues(alpha: 0.45)
                : Colors.black.withValues(alpha: 0.40),
          ),
        ),
      ]),
    );
  }
}

class _PromiseCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final bool isDark;
  final TextTheme tt;
  const _PromiseCard({
    required this.icon, required this.color, required this.title,
    required this.body, required this.isDark, required this.tt,
  });
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.7)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 34, height: 34,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: color.withValues(alpha: 0.12),
            ),
            child: Icon(icon, color: color, size: 17),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: tt.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(body, style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.60)
                      : const Color(0xFF475467),
                  height: 1.55,
                )),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StorageRow extends StatelessWidget {
  final String label;
  final String location;
  final IconData icon;
  final bool isDark;
  final TextTheme tt;
  const _StorageRow({
    required this.label, required this.location, required this.icon,
    required this.isDark, required this.tt,
  });
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Icon(icon, size: 16,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : Colors.black.withValues(alpha: 0.40)),
          const SizedBox(width: 12),
          Expanded(
            child: Text(label, style: tt.bodyMedium?.copyWith(
                fontWeight: FontWeight.w600)),
          ),
          Text(location, style: tt.bodySmall?.copyWith(
            color: isDark
                ? Colors.white.withValues(alpha: 0.45)
                : Colors.black.withValues(alpha: 0.40),
          )),
        ],
      ),
    );
  }
}

class _StorageDivider extends StatelessWidget {
  final bool isDark;
  const _StorageDivider({required this.isDark});
  @override
  Widget build(BuildContext context) {
    return Divider(
      height: 0, thickness: 0.5,
      color: isDark
          ? Colors.white.withValues(alpha: 0.06)
          : Colors.black.withValues(alpha: 0.06),
    );
  }
}

class _NeverRow extends StatelessWidget {
  final String text;
  final bool isDark;
  final TextTheme tt;
  final bool last;
  const _NeverRow({
    required this.text, required this.isDark, required this.tt,
    this.last = false,
  });
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: last ? 0 : 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.close_rounded, size: 16,
              color: const Color(0xFFE24B4A)),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text, style: tt.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
              height: 1.3,
            )),
          ),
        ],
      ),
    );
  }
}
