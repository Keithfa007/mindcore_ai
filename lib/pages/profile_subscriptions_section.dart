
// lib/pages/profile_subscriptions_section.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/subscription_service.dart';

class ProfileSubscriptionsSection extends StatefulWidget {
  const ProfileSubscriptionsSection({super.key});

  @override
  State<ProfileSubscriptionsSection> createState() => _ProfileSubscriptionsSectionState();
}

class _ProfileSubscriptionsSectionState extends State<ProfileSubscriptionsSection> {
  final sub = SubscriptionService();

  @override
  void initState() {
    super.initState();
    sub.init();
  }

  @override
  void dispose() {
    sub.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.all(16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.workspace_premium, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text('Premium Subscription', style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 12),
            Text('Unlock daily coaching, audio and advanced tools.'),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: sub.monthly == null ? null : () => sub.buy(sub.monthly!),
                    child: Text(sub.monthly == null ? 'Monthly (loading...)' : 'Subscribe Monthly'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton(
                    onPressed: sub.yearly == null ? null : () => sub.buy(sub.yearly!),
                    child: Text(sub.yearly == null ? 'Yearly (loading...)' : 'Subscribe Yearly'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextButton(
                    onPressed: () => sub.restore(),
                    child: const Text('Restore purchases'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      // Optional: web/desktop only (provide your portal url)
                      // await StripeService.openPortal('https://your-portal-url');
                    },
                    icon: const Icon(Icons.credit_card),
                    label: const Text('Manage (web portal)'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
