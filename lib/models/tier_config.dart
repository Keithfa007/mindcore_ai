// lib/models/tier_config.dart

enum AppTier { trial, premium, pro }

class TierConfig {
  final AppTier tier;
  final String displayName;
  final int monthlyMessages;
  final int monthlyVoiceSeconds;
  final bool hasVoice;
  final double monthlyPrice;
  final double yearlyPrice;
  final String monthlyProductId;
  final String yearlyProductId;

  // Trial-only daily limits (ignored for paid tiers)
  final int trialDailyMessages;
  final int trialDailyVoiceSeconds;

  const TierConfig._({
    required this.tier,
    required this.displayName,
    required this.monthlyMessages,
    required this.monthlyVoiceSeconds,
    required this.hasVoice,
    required this.monthlyPrice,
    required this.yearlyPrice,
    required this.monthlyProductId,
    required this.yearlyProductId,
    this.trialDailyMessages = -1,
    this.trialDailyVoiceSeconds = -1,
  });

  // ── Tiers ─────────────────────────────────────────────────────────────

  /// 3-day free trial. No payment. 15 messages/day, 5 min voice/day.
  static const TierConfig trial = TierConfig._(
    tier: AppTier.trial,
    displayName: 'Free Trial',
    monthlyMessages: 50,           // fallback monthly cap
    monthlyVoiceSeconds: 5 * 60,   // fallback monthly cap
    hasVoice: true,
    monthlyPrice: 0,
    yearlyPrice: 0,
    monthlyProductId: '',
    yearlyProductId: '',
    trialDailyMessages: 15,
    trialDailyVoiceSeconds: 5 * 60,  // 5 minutes per day
  );

  static const TierConfig premium = TierConfig._(
    tier: AppTier.premium,
    displayName: 'Premium',
    monthlyMessages: 300,
    monthlyVoiceSeconds: 30 * 60,
    hasVoice: true,
    monthlyPrice: 14.99,
    yearlyPrice: 99.99,
    monthlyProductId: 'mindcore_premium_monthly',
    yearlyProductId: 'mindcore_premium_yearly',
  );

  static const TierConfig pro = TierConfig._(
    tier: AppTier.pro,
    displayName: 'Pro',
    monthlyMessages: 600,
    monthlyVoiceSeconds: 60 * 60,
    hasVoice: true,
    monthlyPrice: 25.00,
    yearlyPrice: 179.99,
    monthlyProductId: 'mindcore_pro_monthly',
    yearlyProductId: 'mindcore_pro_yearly',
  );

  static const List<TierConfig> paid = [premium, pro];

  bool get isUnlimited => monthlyMessages == -1;
  bool get isTrial     => tier == AppTier.trial;

  int get voiceMinutes =>
      monthlyVoiceSeconds == -1 ? 999 : (monthlyVoiceSeconds / 60).round();

  String get messageLabel {
    if (isTrial) return '$trialDailyMessages messages / day';
    if (isUnlimited) return 'Unlimited';
    return '$monthlyMessages messages / month';
  }

  String get voiceLabel {
    if (isTrial) return '${(trialDailyVoiceSeconds / 60).round()} min voice / day';
    if (monthlyVoiceSeconds == -1) return 'Unlimited';
    if (monthlyVoiceSeconds == 0) return 'None';
    return '$voiceMinutes min voice / month';
  }

  static TierConfig fromProductId(String productId) {
    if (productId.contains('pro')) return pro;
    if (productId.contains('premium')) return premium;
    return trial;
  }

  static TierConfig fromKey(String? key) {
    switch (key) {
      case 'pro':     return pro;
      case 'premium': return premium;
      default:        return trial;
    }
  }

  String get firestoreKey {
    switch (tier) {
      case AppTier.pro:     return 'pro';
      case AppTier.premium: return 'premium';
      case AppTier.trial:   return 'trial';
    }
  }
}

// ── Voice add-on packs ───────────────────────────────────────────────────────

class VoicePackConfig {
  final String displayName;
  final int minutes;
  final double price;
  final String productId;
  final String tagline;

  const VoicePackConfig({
    required this.displayName,
    required this.minutes,
    required this.price,
    required this.productId,
    required this.tagline,
  });

  static const VoicePackConfig starter = VoicePackConfig(
    displayName: 'Starter Pack', minutes: 30, price: 1.99,
    productId: 'mindcore_voice_starter_30min', tagline: 'Perfect for occasional use',
  );

  static const VoicePackConfig standard = VoicePackConfig(
    displayName: 'Standard Pack', minutes: 60, price: 3.49,
    productId: 'mindcore_voice_standard_60min', tagline: 'Most popular top-up',
  );

  static const VoicePackConfig plus = VoicePackConfig(
    displayName: 'Plus Pack', minutes: 120, price: 5.99,
    productId: 'mindcore_voice_plus_120min', tagline: 'Best per-minute value',
  );

  static const List<VoicePackConfig> all = [starter, standard, plus];

  String get priceLabel => '\u20ac${price.toStringAsFixed(2)}';
  String get minutesLabel => '$minutes min';
}
