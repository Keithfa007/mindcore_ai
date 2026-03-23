// lib/pages/profile_subscriptions_section.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/subscription_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/models/tier_config.dart';

class ProfileSubscriptionsSection extends StatefulWidget {
  const ProfileSubscriptionsSection({super.key});

  @override
  State<ProfileSubscriptionsSection> createState() =>
      _ProfileSubscriptionsSectionState();
}

class _ProfileSubscriptionsSectionState
    extends State<ProfileSubscriptionsSection> {
  final _sub = SubscriptionService();

  @override
  void initState() {
    super.initState();
    _sub.init();
  }

  @override
  void dispose() {
    _sub.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return ValueListenableBuilder<TierConfig>(
      valueListenable: PremiumService.currentTier,
      builder: (context, tier, _) {
        return Card(
          margin: const EdgeInsets.all(16),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.workspace_premium,
                        color: cs.primary),
                    const SizedBox(width: 8),
                    Text('Subscription',
                        style: tt.titleMedium),
                    const Spacer(),
                    if (PremiumService.isPremium.value)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: cs.primaryContainer,
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          tier.displayName,
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: cs.primary,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                if (!PremiumService.isPremium.value) ...[
                  Text('Unlock daily coaching, voice mode and advanced tools.',
                      style: tt.bodyMedium),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () =>
                          Navigator.of(context).pushNamed('/paywall'),
                      child: const Text('See plans'),
                    ),
                  ),
                ] else ...[
                  Text(
                    'You\'re on the ${tier.displayName} plan. '
                    'Manage your subscription in the App Store or Play Store.',
                    style: tt.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () => _sub.restore(),
                    child: const Text('Restore purchases'),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}