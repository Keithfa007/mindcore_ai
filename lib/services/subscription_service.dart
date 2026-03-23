// lib/services/subscription_service.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class SubscriptionService {
  static final SubscriptionService _instance = SubscriptionService._internal();
  factory SubscriptionService() => _instance;
  SubscriptionService._internal();

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _purchaseSub;

  static const Set<String> PRODUCT_IDS = {
    'mindcore_premium_monthly',
    'mindcore_premium_yearly',
    'mindcore_pro_monthly',
    'mindcore_pro_yearly',
  };

  ProductDetails? premiumMonthly;
  ProductDetails? premiumYearly;
  ProductDetails? proMonthly;
  ProductDetails? proYearly;

  bool get isSupported => true;

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
    for (final p in resp.productDetails) {
      switch (p.id) {
        case 'mindcore_premium_monthly': premiumMonthly = p; break;
        case 'mindcore_premium_yearly':  premiumYearly  = p; break;
        case 'mindcore_pro_monthly':     proMonthly     = p; break;
        case 'mindcore_pro_yearly':      proYearly      = p; break;
      }
    }
  }

  Future<void> buy(ProductDetails p) async {
    final param = PurchaseParam(productDetails: p);
    await _iap.buyNonConsumable(purchaseParam: param);
  }

  Future<void> restore() async {
    await _iap.restorePurchases();
  }

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
    final tierConfig = TierConfig.fromProductId(p.productID);
    await PremiumService.activate(tier: tierConfig);
    debugPrint('SubscriptionService: activated ${tierConfig.displayName}');
  }

  void dispose() {
    _purchaseSub?.cancel();
    _purchaseSub = null;
  }
}