// lib/models/tier_config.dart

enum AppTier {
  trial,
  premium,
  pro,
}

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
  });

  static const TierConfig trial = TierConfig._(
    tier: AppTier.trial,
    displayName: 'Trial',
    monthlyMessages: 50,
    monthlyVoiceSeconds: 5 * 60, // 5 minutes
    hasVoice: true,
    monthlyPrice: 0,
    yearlyPrice: 0,
    monthlyProductId: '',
    yearlyProductId: '',
  );

  static const TierConfig premium = TierConfig._(
    tier: AppTier.premium,
    displayName: 'Premium',
    monthlyMessages: 150,
    monthlyVoiceSeconds: 15 * 60,
    hasVoice: true,
    monthlyPrice: 14.99,
    yearlyPrice: 99.99,
    monthlyProductId: 'mindcore_premium_monthly',
    yearlyProductId: 'mindcore_premium_yearly',
  );

  static const TierConfig pro = TierConfig._(
    tier: AppTier.pro,
    displayName: 'Pro',
    monthlyMessages: 300,
    monthlyVoiceSeconds: 30 * 60,
    hasVoice: true,
    monthlyPrice: 25.00,
    yearlyPrice: 179.99,
    monthlyProductId: 'mindcore_pro_monthly',
    yearlyProductId: 'mindcore_pro_yearly',
  );

  static const List<TierConfig> paid = [premium, pro];

  bool get isUnlimited => monthlyMessages == -1;

  int get voiceMinutes =>
      monthlyVoiceSeconds == -1 ? 999 : (monthlyVoiceSeconds / 60).round();

  String get messageLabel =>
      isUnlimited ? 'Unlimited' : '$monthlyMessages / month';

  String get voiceLabel => monthlyVoiceSeconds == -1
      ? 'Unlimited'
      : monthlyVoiceSeconds == 0
          ? 'None'
          : '$voiceMinutes min / month';

  static TierConfig fromProductId(String productId) {
    if (productId.contains('pro')) return pro;
    if (productId.contains('premium')) return premium;
    return trial;
  }

  static TierConfig fromKey(String? key) {
    switch (key) {
      case 'pro':
        return pro;
      case 'premium':
        return premium;
      default:
        return trial;
    }
  }

  String get firestoreKey {
    switch (tier) {
      case AppTier.pro:
        return 'pro';
      case AppTier.premium:
        return 'premium';
      case AppTier.trial:
        return 'trial';
    }
  }
}
