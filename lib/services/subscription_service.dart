
// lib/services/subscription_service.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:mindcore_ai/env/env.dart';

final publishable = Env.stripePublishable;
final secret = Env.stripeSecret;


class SubscriptionService {
  static final SubscriptionService _instance = SubscriptionService._internal();
  factory SubscriptionService() => _instance;
  SubscriptionService._internal();

  final InAppPurchase _iap = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _purchaseSub;

  static const Set<String> PRODUCT_IDS = {
    'mindcore_premium_monthly',
    'mindcore_premium_yearly',
  };

  ProductDetails? monthly;
  ProductDetails? yearly;

  bool get isSupported => true;

  Future<void> init() async {
    final available = await _iap.isAvailable();
    if (!available) return;
    _purchaseSub ??= _iap.purchaseStream.listen(_onPurchaseUpdated, onDone: () {
      _purchaseSub?.cancel();
    }, onError: (e) {
      debugPrint('IAP stream error: $e');
    });
    await _queryProducts();
  }

  Future<void> _queryProducts() async {
    final resp = await _iap.queryProductDetails(PRODUCT_IDS);
    if (resp.error != null) {
      debugPrint('IAP query error: ${resp.error}');
      return;
    }
    for (final p in resp.productDetails) {
      if (p.id == 'mindcore_premium_monthly') monthly = p;
      if (p.id == 'mindcore_premium_yearly') yearly = p;
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
          await _finish(purchase);
          break;
        case PurchaseStatus.pending:
          break;
        case PurchaseStatus.error:
          debugPrint('Purchase error: ${purchase.error}');
          break;
        case PurchaseStatus.canceled:
          break;
      }
    }
  }

  Future<void> _finish(PurchaseDetails p) async {
    if (p.pendingCompletePurchase) {
      await _iap.completePurchase(p);
    }
  }

  void dispose() {
    _purchaseSub?.cancel();
    _purchaseSub = null;
  }
}
