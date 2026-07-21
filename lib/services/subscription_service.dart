// lib/services/subscription_service.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:in_app_purchase_android/in_app_purchase_android.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/services/usage_service.dart';

class SubscriptionService {
  static final SubscriptionService _instance = SubscriptionService._internal();
  factory SubscriptionService() => _instance;
  SubscriptionService._internal();

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _purchaseSub;

  // ── Product ID sets ────────────────────────────────────────────────────

  static const Set<String> _subscriptionIds = {
    'mindcore_premium_monthly',
    'mindcore_premium_yearly',
    'mindcore_pro_monthly',
    'mindcore_pro_yearly',
  };

  static const Set<String> _consumableIds = {
    'mindcore_voice_starter_30min',
    'mindcore_voice_standard_60min',
    'mindcore_voice_plus_120min',
  };

  static Set<String> get PRODUCT_IDS => {
        ..._subscriptionIds,
        ..._consumableIds,
      };

  // ── Cached product details ─────────────────────────────────────────────

  ProductDetails? trialProduct;
  // Base plan (recurring price shown on the card / banner).
  ProductDetails? premiumMonthly;
  // The free-trial offer (used to launch the actual 3-day trial).
  ProductDetails? premiumMonthlyOffer;
  ProductDetails? premiumYearly;
  ProductDetails? proMonthly;
  ProductDetails? proYearly;

  // Voice pack products keyed by product ID
  final Map<String, ProductDetails> _voicePacks = {};

  /// Returns the ProductDetails for a given voice pack product ID, or null.
  ProductDetails? voicePackProduct(String productId) => _voicePacks[productId];

  /// What to purchase for the 3-day free trial. Falls back to the base plan
  /// if the trial offer is unavailable (e.g. the user is not eligible).
  ProductDetails? get premiumTrialPurchase => premiumMonthlyOffer ?? premiumMonthly;

  bool get isSupported => true;

  // ── Init & product loading ─────────────────────────────────────────────

  Future<void> init() async {
    final available = await _iap.isAvailable();
    if (!available) return;

    _purchaseSub ??= _iap.purchaseStream.listen(
      _onPurchaseUpdated,
      onDone: () => _purchaseSub?.cancel(),
      onError: (e) => debugPrint('IAP stream error: $e'),
    );

    await _queryProducts();
  }

  Future<void> _queryProducts() async {
    final resp = await _iap.queryProductDetails(PRODUCT_IDS);
    if (resp.error != null) {
      debugPrint('IAP query error: ${resp.error}');
      return;
    }
    // A subscription with a base plan AND a free-trial offer comes back as
    // multiple ProductDetails sharing the same id, one per offer. Keep the
    // base plan for price display and the free-trial offer for the trial.
    for (final p in resp.productDetails) {
      switch (p.id) {
        case 'mindcore_trial_7day':
          trialProduct = p;
          break;
        case 'mindcore_premium_monthly':
          if (_hasFreeTrial(p)) {
            premiumMonthlyOffer = p;
          } else {
            premiumMonthly = p;
          }
          break;
        case 'mindcore_premium_yearly':
          if (!_hasFreeTrial(p)) premiumYearly = p;
          break;
        case 'mindcore_pro_monthly':
          if (!_hasFreeTrial(p)) proMonthly = p;
          break;
        case 'mindcore_pro_yearly':
          if (!_hasFreeTrial(p)) proYearly = p;
          break;
        case 'mindcore_voice_starter_30min':
        case 'mindcore_voice_standard_60min':
        case 'mindcore_voice_plus_120min':
          _voicePacks[p.id] = p;
          break;
      }
    }
    // If only the trial offer came back (no separate base plan), use it for
    // display too so we never render a null price.
    premiumMonthly ??= premiumMonthlyOffer;
    debugPrint('SubscriptionService: base=${premiumMonthly != null} '
        'trialOffer=${premiumMonthlyOffer != null}');
  }

  /// True if this Google Play product/offer includes a free (zero-cost) phase.
  bool _hasFreeTrial(ProductDetails p) {
    if (p is! GooglePlayProductDetails) return false;
    final offers = p.productDetails.subscriptionOfferDetails;
    if (offers == null) return false;
    for (final offer in offers) {
      // Only inspect the offer that matches THIS ProductDetails' token.
      if (offer.offerIdToken != p.offerToken) continue;
      if (offer.offerId == 'free-trial-3day') return true;
      for (final phase in offer.pricingPhases) {
        if (phase.priceAmountMicros == 0) return true;
      }
    }
    return false;
  }

  // ── Purchase ──────────────────────────────────────────────────────────

  Future<void> buy(ProductDetails p) async {
    final isConsumable = _consumableIds.contains(p.id);
    final param = PurchaseParam(productDetails: p);
    if (isConsumable) {
      await _iap.buyConsumable(purchaseParam: param);
    } else {
      await _iap.buyNonConsumable(purchaseParam: param);
    }
  }

  Future<void> restore() async {
    await _iap.restorePurchases();
  }

  // ── Purchase stream handler ───────────────────────────────────────────

  void _onPurchaseUpdated(List<PurchaseDetails> purchases) async {
    for (final purchase in purchases) {
      switch (purchase.status) {
        case PurchaseStatus.purchased:
        case PurchaseStatus.restored:
          await _handleSuccess(purchase);
          break;
        case PurchaseStatus.error:
          debugPrint('Purchase error: ${purchase.error}');
          break;
        case PurchaseStatus.pending:
        case PurchaseStatus.canceled:
          break;
      }
    }
  }

  Future<void> _handleSuccess(PurchaseDetails p) async {
    if (p.pendingCompletePurchase) {
      await _iap.completePurchase(p);
    }

    // Voice pack — add minutes to the user's balance
    if (_consumableIds.contains(p.productID)) {
      final pack = VoicePackConfig.all
          .where((v) => v.productId == p.productID)
          .firstOrNull;
      if (pack != null) {
        await UsageService.instance.addVoiceMinutes(pack.minutes);
        debugPrint(
            'SubscriptionService: added ${pack.minutes} voice minutes');
      }
      return;
    }

    // Subscription — activate tier
    final tierConfig = TierConfig.fromProductId(p.productID);
    await PremiumService.activate(tier: tierConfig);
    debugPrint('SubscriptionService: activated ${tierConfig.displayName}');
  }

  void dispose() {
    _purchaseSub?.cancel();
    _purchaseSub = null;
  }
}
