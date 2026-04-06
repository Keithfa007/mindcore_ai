// lib/pages/paywall_screen.dart
import 'package:flutter/material.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/subscription_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class PaywallScreen extends StatefulWidget {
  const PaywallScreen({super.key});

  @override
  State<PaywallScreen> createState() => _PaywallScreenState();
}

class _PaywallScreenState extends State<PaywallScreen> {
  final _sub = SubscriptionService();
  bool _loading = false;
  bool _selectedYearly = false;

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

  void _onPremiumChanged() {
    if (PremiumService.isPremium.value && mounted) Navigator.of(context).pop();
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
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final currentTier = PremiumService.currentTier.value;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Column(
            children: [
              // ── Header bar ────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                child: Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.close,
                          color: isDark ? Colors.white70 : Colors.black54),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                    const Spacer(),
                    TextButton(
                      onPressed: _loading ? null : _restore,
                      child: Text('Restore',
                          style: tt.labelSmall?.copyWith(
                              color: AppColors.primary,
                              fontWeight: FontWeight.w700)),
                    ),
                  ],
                ),
              ),

              Expanded(
                child: SingleChildScrollView(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Heading
                      Icon(Icons.workspace_premium_rounded,
                          size: 40, color: AppColors.primary),
                      const SizedBox(height: 10),
                      Text('Choose your plan',
                          textAlign: TextAlign.center,
                          style: tt.headlineSmall?.copyWith(
                              fontWeight: FontWeight.w900,
                              letterSpacing: -0.6,
                              color: isDark
                                  ? Colors.white
                                  : const Color(0xFF0E1320))),
                      const SizedBox(height: 6),
                      Text(
                        'AI chat, voice, guided sessions and more.\nCancel anytime.',
                        textAlign: TextAlign.center,
                        style: tt.bodyMedium?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.50)
                                : const Color(0xFF475467),
                            height: 1.5),
                      ),
                      const SizedBox(height: 20),

                      // ── Billing toggle ─────────────────────────────────
                      Row(
                        children: [
                          _Toggle(
                              label: 'Monthly',
                              selected: !_selectedYearly,
                              onTap: () =>
                                  setState(() => _selectedYearly = false)),
                          const SizedBox(width: 10),
                          _Toggle(
                              label: 'Yearly',
                              badge: 'Save ~44%',
                              selected: _selectedYearly,
                              onTap: () =>
                                  setState(() => _selectedYearly = true)),
                        ],
                      ),
                      const SizedBox(height: 16),

                      // ── Trial card ───────────────────────────────────
                      if (currentTier.tier == AppTier.trial) ...[
                        _TrialCard(
                            loading: _loading,
                            product: _sub.trialProduct,
                            onBuy: _buy,
                            isDark: isDark,
                            tt: tt),
                        const SizedBox(height: 10),
                      ],

                      // ── Premium card ────────────────────────────────
                      _PlanCard(
                        config: TierConfig.premium,
                        yearly: _selectedYearly,
                        product: _selectedYearly
                            ? _sub.premiumYearly
                            : _sub.premiumMonthly,
                        loading: _loading,
                        onBuy: _buy,
                        isCurrent: currentTier.tier == AppTier.premium,
                        accentColor: AppColors.primary,
                        glowColor: AppColors.glowBlue,
                        isDark: isDark,
                        tt: tt,
                      ),
                      const SizedBox(height: 10),

                      // ── Pro card ────────────────────────────────────
                      _PlanCard(
                        config: TierConfig.pro,
                        yearly: _selectedYearly,
                        product: _selectedYearly
                            ? _sub.proYearly
                            : _sub.proMonthly,
                        loading: _loading,
                        onBuy: _buy,
                        featured: true,
                        isCurrent: currentTier.tier == AppTier.pro,
                        accentColor: AppColors.violet,
                        glowColor: AppColors.glowViolet,
                        isDark: isDark,
                        tt: tt,
                      ),
                      const SizedBox(height: 24),

                      // ── Voice add-on packs ───────────────────────────
                      if (currentTier.tier != AppTier.trial) ...[  
                        _VoiceAddOnSection(
                            loading: _loading,
                            onBuy: _buy,
                            sub: _sub,
                            isDark: isDark,
                            tt: tt),
                        const SizedBox(height: 20),
                      ],

                      // Footer
                      Text(
                        'Subscriptions renew automatically. Cancel anytime\nin App Store or Google Play settings.',
                        style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.30)
                                : Colors.black.withValues(alpha: 0.30),
                            height: 1.5),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 24),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Billing toggle ────────────────────────────────────────────────────────

class _Toggle extends StatelessWidget {
  final String label;
  final bool selected;
  final String? badge;
  final VoidCallback onTap;
  const _Toggle(
      {required this.label,
      required this.selected,
      required this.onTap,
      this.badge});

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          padding:
              const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
          decoration: BoxDecoration(
            color: selected
                ? AppColors.primary.withValues(alpha: isDark ? 0.18 : 0.10)
                : (isDark
                    ? Colors.white.withValues(alpha: 0.05)
                    : Colors.black.withValues(alpha: 0.04)),
            border: Border.all(
              color: selected
                  ? AppColors.primary
                  : (isDark
                      ? Colors.white.withValues(alpha: 0.12)
                      : Colors.black.withValues(alpha: 0.10)),
              width: selected ? 1.5 : 0.8,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Text(label,
                  style: tt.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: selected ? AppColors.primary : null)),
              if (badge != null)
                Text(badge!,
                    style: TextStyle(
                        fontSize: 10,
                        color: selected
                            ? AppColors.primary
                            : (isDark
                                ? Colors.white.withValues(alpha: 0.40)
                                : Colors.black.withValues(alpha: 0.40)))),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Trial card ───────────────────────────────────────────────────────────

class _TrialCard extends StatelessWidget {
  final bool loading;
  final ProductDetails? product;
  final Future<void> Function(ProductDetails?) onBuy;
  final bool isDark;
  final TextTheme tt;
  const _TrialCard(
      {required this.loading,
      required this.product,
      required this.onBuy,
      required this.isDark,
      required this.tt});

  @override
  Widget build(BuildContext context) {
    final accent = const Color(0xFF64748B);
    return GlassCard(
      glowColor: accent.withValues(alpha: 0.20),
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(6),
                    border:
                        Border.all(color: accent.withValues(alpha: 0.30)),
                  ),
                  child: Text('7-DAY TRIAL',
                      style: tt.labelSmall?.copyWith(
                          color: accent, fontWeight: FontWeight.w800,
                          fontSize: 10)),
                ),
                const SizedBox(height: 8),
                Text('Try everything free',
                    style: tt.titleMedium?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: isDark ? Colors.white : const Color(0xFF0E1320))),
                const SizedBox(height: 4),
                Text('50 messages • 5 min voice • All features',
                    style: tt.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.55)
                            : const Color(0xFF475467))),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            children: [
              Text('€1.99',
                  style: tt.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900, color: accent)),
              Text('one-time',
                  style: tt.bodySmall
                      ?.copyWith(color: accent.withValues(alpha: 0.70))),
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: loading ? null : () => onBuy(product),
                style: OutlinedButton.styleFrom(
                    side: BorderSide(color: accent),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8)),
                child: Text('Start',
                    style: TextStyle(
                        color: accent, fontWeight: FontWeight.w800)),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Plan card ────────────────────────────────────────────────────────────

class _PlanCard extends StatelessWidget {
  final TierConfig config;
  final bool yearly;
  final ProductDetails? product;
  final bool loading;
  final bool featured;
  final bool isCurrent;
  final Color accentColor;
  final Color glowColor;
  final Future<void> Function(ProductDetails?) onBuy;
  final bool isDark;
  final TextTheme tt;

  const _PlanCard({
    required this.config,
    required this.yearly,
    required this.product,
    required this.loading,
    required this.onBuy,
    required this.isCurrent,
    required this.accentColor,
    required this.glowColor,
    required this.isDark,
    required this.tt,
    this.featured = false,
  });

  @override
  Widget build(BuildContext context) {
    final price    = yearly ? config.yearlyPrice : config.monthlyPrice;
    final interval = yearly ? '/year' : '/mo';
    final display  = product?.price ?? '€${price.toStringAsFixed(2)}';

    return GlassCard(
      glowColor: glowColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        if (featured)
                          Container(
                            margin: const EdgeInsets.only(right: 8),
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: accentColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                  color:
                                      accentColor.withValues(alpha: 0.35)),
                            ),
                            child: Text('BEST VALUE',
                                style: tt.labelSmall?.copyWith(
                                    color: accentColor,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 10)),
                          ),
                        if (isCurrent)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: const Color(0xFF1D9E75)
                                  .withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text('CURRENT',
                                style: tt.labelSmall?.copyWith(
                                    color: const Color(0xFF1D9E75),
                                    fontWeight: FontWeight.w800,
                                    fontSize: 10)),
                          ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(config.displayName,
                        style: tt.titleLarge?.copyWith(
                            fontWeight: FontWeight.w900,
                            color: isDark
                                ? Colors.white
                                : const Color(0xFF0E1320),
                            letterSpacing: -0.5)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(display,
                      style: tt.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w900,
                          color: accentColor,
                          letterSpacing: -0.5)),
                  Text(interval,
                      style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.45)
                              : Colors.black.withValues(alpha: 0.45))),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          _FeatureRow(icon: Icons.chat_rounded,
              label: config.messageLabel, color: accentColor),
          _FeatureRow(icon: Icons.mic_rounded,
              label: config.voiceLabel, color: accentColor),
          _FeatureRow(icon: Icons.self_improvement_rounded,
              label: 'All guided sessions & breathing tools',
              color: accentColor),
          _FeatureRow(icon: Icons.insights_rounded,
              label: 'Mood history, streak & weekly AI report',
              color: accentColor),
          _FeatureRow(icon: Icons.star_rounded,
              label: 'SOS grounding mode & daily briefing',
              color: accentColor),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: isCurrent
                ? Container(
                    padding: const EdgeInsets.symmetric(vertical: 13),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1D9E75).withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                          color: const Color(0xFF1D9E75)
                              .withValues(alpha: 0.35)),
                    ),
                    child: Text('Your current plan',
                        textAlign: TextAlign.center,
                        style: tt.labelLarge?.copyWith(
                            color: const Color(0xFF1D9E75),
                            fontWeight: FontWeight.w700)),
                  )
                : FilledButton(
                    onPressed: loading ? null : () => onBuy(product),
                    style: FilledButton.styleFrom(
                      backgroundColor: accentColor,
                      minimumSize: const Size.fromHeight(48),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                    ),
                    child: loading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : Text('Get ${config.displayName}',
                            style: const TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800)),
                  ),
          ),
        ],
      ),
    );
  }
}

// ── Voice add-on section ─────────────────────────────────────────────────

class _VoiceAddOnSection extends StatelessWidget {
  final bool loading;
  final Future<void> Function(ProductDetails?) onBuy;
  final SubscriptionService sub;
  final bool isDark;
  final TextTheme tt;
  const _VoiceAddOnSection(
      {required this.loading,
      required this.onBuy,
      required this.sub,
      required this.isDark,
      required this.tt});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.mic_rounded, color: AppColors.mintDeep, size: 16),
            const SizedBox(width: 8),
            Text('Voice Minute Top-Ups',
                style: tt.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: AppColors.mintDeep)),
          ],
        ),
        const SizedBox(height: 4),
        Text('Run out of voice minutes? Buy more instantly.',
            style: tt.bodySmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.50)
                    : const Color(0xFF475467))),
        const SizedBox(height: 12),
        ...VoicePackConfig.all.map((pack) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _VoicePackCard(
                  pack: pack,
                  loading: loading,
                  product: sub.voicePackProduct(pack.productId),
                  onBuy: onBuy,
                  isDark: isDark,
                  tt: tt),
            )),
      ],
    );
  }
}

class _VoicePackCard extends StatelessWidget {
  final VoicePackConfig pack;
  final bool loading;
  final ProductDetails? product;
  final Future<void> Function(ProductDetails?) onBuy;
  final bool isDark;
  final TextTheme tt;
  const _VoicePackCard(
      {required this.pack,
      required this.loading,
      required this.product,
      required this.onBuy,
      required this.isDark,
      required this.tt});

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      glowColor: AppColors.glowMint,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.mintDeep.withValues(alpha: 0.12),
              border: Border.all(
                  color: AppColors.mintDeep.withValues(alpha: 0.30)),
            ),
            child: Icon(Icons.mic_rounded,
                color: AppColors.mintDeep, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(pack.displayName,
                    style: tt.titleSmall?.copyWith(
                        fontWeight: FontWeight.w800)),
                Text(
                    '${pack.minutesLabel} voice • ${pack.tagline}',
                    style: tt.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.50)
                            : const Color(0xFF475467))),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(pack.priceLabel,
                  style: tt.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: AppColors.mintDeep)),
              const SizedBox(height: 4),
              SizedBox(
                height: 32,
                child: FilledButton(
                  onPressed: loading ? null : () => onBuy(product),
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.mintDeep,
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8)),
                  ),
                  child: Text('Buy',
                      style: tt.labelSmall?.copyWith(
                          color: Colors.white,
                          fontWeight: FontWeight.w800)),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

// ── Small helpers ──────────────────────────────────────────────────────────

class _FeatureRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _FeatureRow(
      {required this.icon, required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.70)
                        : const Color(0xFF475467))),
          ),
        ],
      ),
    );
  }
}
