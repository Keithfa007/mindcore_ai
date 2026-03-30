// lib/pages/paywall_screen.dart
import 'package:flutter/material.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/subscription_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class PaywallScreen extends StatefulWidget {
  const PaywallScreen({super.key});

  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> {
  final _sub = SubscriptionService();
  bool _loading = false;
  bool _selectedYearly = true;

  static const List<List<dynamic>> _benefits = [
    [Icons.chat_rounded,             'AI conversations that adapt to your mood'],
    [Icons.record_voice_over_rounded,'Hands-free push-to-talk voice mode'],
    [Icons.self_improvement_rounded, 'All guided sessions and breathing tools'],
    [Icons.headphones_rounded,       'Full relaxation audio library'],
    [Icons.auto_awesome_rounded,     'Daily insight engine and journal AI'],
    [Icons.picture_as_pdf_rounded,   'Export your journal as PDF'],
  ];

  @override
  void initState() {
    super.initState();
    _sub.init();
    PremiumService.isPremium.addListener(_onPremiumChanged);
  }

  @override
  void dispose() {
    PremiumService.isPremium.removeListener(_onPremiumChanged);
    _sub.dispose();
    super.dispose();
  }

  // Called when subscription completes — pop back so the gate screen
  // can detect the premium change and let the user through.
  void _onPremiumChanged() {
    if (PremiumService.isPremium.value && mounted) {
      Navigator.of(context).pop();
    }
  }

  // ✅ Read gateMode HERE, at button-press time, when the route is
  // fully active and ModalRoute.of(context) is guaranteed non-null.
  // didChangeDependencies fires too early (route not settled yet).
  void _handleClose() {
    final args = ModalRoute.of(context)?.settings.arguments;
    final isGateMode = args is Map && args['gateMode'] == true;

    if (isGateMode && !PremiumService.isPremium.value) {
      // Clear the whole stack and go home — prevents black page or
      // returning to a locked screen.
      Navigator.of(context)
          .pushNamedAndRemoveUntil('/home', (route) => false);
    } else {
      Navigator.of(context).pop();
    }
  }

  Future<void> _buy(ProductDetails? product) async {
    if (product == null) return;
    setState(() => _loading = true);
    try {
      await _sub.buy(product);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _restore() async {
    setState(() => _loading = true);
    await _sub.restore();
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Scaffold(
      backgroundColor: cs.surface,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: _handleClose,
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.workspace_premium_rounded,
                  size: 44, color: cs.primary),
              const SizedBox(height: 10),
              Text('MindCore Premium',
                  style: tt.headlineMedium,
                  textAlign: TextAlign.center),
              const SizedBox(height: 6),
              Text(
                'Your full mental wellness toolkit — AI chat, voice, '
                'guided sessions and more.',
                style: tt.bodyMedium
                    ?.copyWith(color: cs.onSurface.withOpacity(0.55)),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 22),

              // Benefits
              ...(_benefits.map((b) => Padding(
                    padding: const EdgeInsets.symmetric(vertical: 5),
                    child: Row(
                      children: [
                        Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(
                            color: cs.primary.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(9),
                          ),
                          child: Icon(b[0] as IconData, size: 16, color: cs.primary),
                        ),
                        const SizedBox(width: 12),
                        Expanded(child: Text(b[1] as String, style: tt.bodyMedium)),
                      ],
                    ),
                  ))),
              const SizedBox(height: 24),

              // Billing toggle
              Row(
                children: [
                  _BillingToggle(
                    label: 'Monthly',
                    selected: !_selectedYearly,
                    onTap: () => setState(() => _selectedYearly = false),
                  ),
                  const SizedBox(width: 10),
                  _BillingToggle(
                    label: 'Yearly',
                    selected: _selectedYearly,
                    badge: 'Save up to 44%',
                    onTap: () => setState(() => _selectedYearly = true),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Tier cards
              _TierCard(
                config: TierConfig.premium,
                yearly: _selectedYearly,
                product: _selectedYearly
                    ? _sub.premiumYearly
                    : _sub.premiumMonthly,
                loading: _loading,
                onBuy: _buy,
              ),
              const SizedBox(height: 10),
              _TierCard(
                config: TierConfig.pro,
                yearly: _selectedYearly,
                product: _selectedYearly
                    ? _sub.proYearly
                    : _sub.proMonthly,
                loading: _loading,
                onBuy: _buy,
                featured: true,
              ),
              const SizedBox(height: 20),

              // Restore
              TextButton(
                onPressed: _loading ? null : _restore,
                child: Text(
                  'Restore purchases',
                  style: tt.bodySmall?.copyWith(
                    color: cs.onSurface.withOpacity(0.4),
                  ),
                ),
              ),
              Text(
                'Subscriptions renew automatically. '
                'Cancel anytime in App Store or Play Store settings.',
                style: tt.bodySmall
                    ?.copyWith(color: cs.onSurface.withOpacity(0.3)),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

class _BillingToggle extends StatelessWidget {
  final String label;
  final bool selected;
  final String? badge;
  final VoidCallback onTap;

  const _BillingToggle({
    required this.label,
    required this.selected,
    required this.onTap,
    this.badge,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
          decoration: BoxDecoration(
            color: selected
                ? cs.primaryContainer
                : cs.surfaceVariant.withOpacity(0.5),
            border: Border.all(
              color: selected ? cs.primary : Colors.transparent,
              width: 1.5,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            children: [
              Text(
                label,
                style: tt.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: selected ? cs.primary : null,
                ),
              ),
              if (badge != null)
                Text(
                  badge!,
                  style: TextStyle(
                    fontSize: 10,
                    color: selected
                        ? cs.primary
                        : cs.onSurface.withOpacity(0.45),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TierCard extends StatelessWidget {
  final TierConfig config;
  final bool yearly;
  final ProductDetails? product;
  final bool loading;
  final bool featured;
  final Future<void> Function(ProductDetails?) onBuy;

  const _TierCard({
    required this.config,
    required this.yearly,
    required this.product,
    required this.loading,
    required this.onBuy,
    this.featured = false,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    final price    = yearly ? config.yearlyPrice : config.monthlyPrice;
    final interval = yearly ? '/year' : '/month';
    final storePrice = product?.price ?? '€${price.toStringAsFixed(2)}';

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surface,
        border: Border.all(
          color: featured ? cs.primary : cs.outlineVariant.withOpacity(0.5),
          width: featured ? 2 : 0.5,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (featured)
                    Container(
                      margin: const EdgeInsets.only(bottom: 4),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: cs.primaryContainer,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'Most popular',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                          color: cs.primary,
                        ),
                      ),
                    ),
                  Text(config.displayName,
                      style: tt.titleMedium
                          ?.copyWith(fontWeight: FontWeight.w700)),
                ],
              ),
              const Spacer(),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(storePrice,
                      style: tt.titleLarge
                          ?.copyWith(fontWeight: FontWeight.w700)),
                  Text(interval,
                      style: tt.bodySmall?.copyWith(
                          color: cs.onSurface.withOpacity(0.45))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          _FeatureRow(icon: Icons.chat_rounded,    label: config.messageLabel),
          _FeatureRow(icon: Icons.mic_rounded,     label: config.voiceLabel),
          _FeatureRow(icon: Icons.star_rounded,    label: 'All features included'),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: featured
                ? FilledButton(
                    onPressed: loading ? null : () => onBuy(product),
                    style: FilledButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: loading
                        ? const SizedBox(
                            width: 18, height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Text('Get Pro'),
                  )
                : OutlinedButton(
                    onPressed: loading ? null : () => onBuy(product),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text('Get Premium'),
                  ),
          ),
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  final IconData icon;
  final String label;
  const _FeatureRow({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon, size: 14, color: cs.primary.withOpacity(0.8)),
          const SizedBox(width: 8),
          Text(label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: cs.onSurface.withOpacity(0.7))),
        ],
      ),
    );
  }
}
