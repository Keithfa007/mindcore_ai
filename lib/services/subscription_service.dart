// lib/services/subscription_service.dart
import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
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

  /// Surfaces the last user-facing purchase error to the UI (the paywall
  /// listens to this and shows a SnackBar). Null when there is no pending error.
  final ValueNotifier<String?> purchaseError = ValueNotifier<String?>(null);

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

  /// True when the real free-trial offer was resolved from Google Play.
  /// When false, "Start Free Trial" would fall back to the full-price base
  /// plan — used by diagnostics and (later) to guard the trial button.
  bool get hasTrialOffer => premiumMonthlyOffer != null;

  bool get isSupported => true;

  // ── Diagnostics ─────────────────────────────────────────────────────────
  // Best-effort logging so billing/trial failures are visible in production
  // (where debugPrint is stripped from release builds). Written to the
  // signed-in user's own doc under `billingDiag` — the Firestore rules allow
  // the owner to write their own user doc. Never throws: diagnostics must
  // never break the purchase flow.

  Future<void> _log(String event, [Map<String, dynamic> data = const {}]) async {
    debugPrint('SubscriptionService[$event]: $data');
    try {
      final uid = FirebaseAuth.instance.currentUser?.uid;
      if (uid == null) return;
      await FirebaseFirestore.instance.collection('users').doc(uid).set({
        'billingDiag': {
          event: {...data, 'ts': DateTime.now().toIso8601String()},
        },
        'billingDiagAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (_) {
      // Diagnostics must never break the purchase flow.
    }
  }

  Map<String, dynamic> _describe(ProductDetails? p) {
    if (p == null) return {'product': null};
    final m = <String, dynamic>{'product': p.id, 'price': p.price};
    if (p is GooglePlayProductDetails) {
      m['offerToken'] = p.offerToken == null ? 'null' : 'present';
      final offers = p.productDetails.subscriptionOfferDetails;
      if (offers != null) {
        for (final o in offers) {
          if (o.offerIdToken == p.offerToken) {
            m['offerId'] = o.offerId;
            break;
          }
        }
      }
    }
    return m;
  }

  // ── Init & product loading ─────────────────────────────────────────────

  Future<void> init() async {
    final available = await _iap.isAvailable();
    if (!available) {
      await _log('store_unavailable');
      return;
    }

    _purchaseSub ??= _iap.purchaseStream.listen(
      _onPurchaseUpdated,
      onDone: () => _purchaseSub?.cancel(),
      onError: (e) {
        debugPrint('IAP stream error: $e');
        _log('stream_error', {'error': e.toString()});
      },
    );

    await _queryProducts();
  }

  Future<void> _queryProducts() async {
    final resp = await _iap.queryProductDetails(PRODUCT_IDS);
    if (resp.error != null) {
      debugPrint('IAP query error: ${resp.error}');
      await _log('query_error', {'error': resp.error.toString()});
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
    await _log('products_loaded', {
      'count': resp.productDetails.length,
      'notFound': resp.notFoundIDs,
      'trialResolved': premiumMonthlyOffer != null,
      'base': _describe(premiumMonthly),
      'trialOffer': _describe(premiumMonthlyOffer),
    });
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
    await _log('buy_attempt', {
      ..._describe(p),
      'isTrialOffer': identical(p, premiumMonthlyOffer),
      'consumable': isConsumable,
    });
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
          purchaseError.value =
              purchase.error?.message ?? 'Purchase failed. Please try again.';
          await _log('purchase_error', {
            'product': purchase.productID,
            'code': purchase.error?.code,
            'message': purchase.error?.message,
            'details': purchase.error?.details?.toString(),
          });
          break;
        case PurchaseStatus.canceled:
          await _log('purchase_canceled', {'product': purchase.productID});
          break;
        case PurchaseStatus.pending:
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
      await _log('purchase_success', {'product': p.productID, 'type': 'voice'});
      return;
    }

    // Subscription — activate tier
    final tierConfig = TierConfig.fromProductId(p.productID);
    await PremiumService.activate(tier: tierConfig);
    debugPrint('SubscriptionService: activated ${tierConfig.displayName}');
    await _log('purchase_success',
        {'product': p.productID, 'tier': tierConfig.displayName});
  }

  void dispose() {
    _purchaseSub?.cancel();
    _purchaseSub = null;
  }
}
