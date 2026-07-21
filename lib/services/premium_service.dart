// lib/services/premium_service.dart
//
// Access model: a user can use MindCore AI only with an ACTIVE Google Play
// free trial or subscription (isPremium == true). There is no separate
// in-app free trial. A user who has not started the Google Play free trial
// (or subscribed) has no access and is routed to the paywall.
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/notification_service.dart';

class PremiumService {
  PremiumService._();

  static final isPremium   = ValueNotifier<bool>(false);
  static final currentTier = ValueNotifier<TierConfig>(TierConfig.trial);

  static const _kIsPremium = 'mindcore_is_premium';
  static const _kTierKey   = 'mindcore_tier_key';

  static bool _initialised = false;
  static bool _loaded = false;
  static Future<void>? _refreshOp;

  // ── Init ────────────────────────────────────────────────────────────────

  static Future<void> init() async {
    if (_initialised) return;
    _initialised = true;

    final prefs = await SharedPreferences.getInstance();
    isPremium.value   = prefs.getBool(_kIsPremium) ?? false;
    currentTier.value = TierConfig.fromKey(prefs.getString(_kTierKey));

    FirebaseAuth.instance.authStateChanges().listen((user) async {
      if (user == null) {
        _loaded = false;
        await _setLocal(false, TierConfig.trial);
        return;
      }
      await _refreshFromFirestore(user.uid);
    });
  }

  // ── Access ──────────────────────────────────────────────────────────────

  static Future<void> _ensureLoaded() async {
    if (_loaded) return;
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    await _refreshFromFirestore(uid);
  }

  /// Access is granted only with an active subscription or Google Play trial.
  static Future<bool> hasAccess() async {
    await _ensureLoaded();
    return isPremium.value;
  }

  // Legacy helpers kept for existing callers. Access is now purely isPremium.
  static Future<bool> isTrialWindowOpen() async {
    await _ensureLoaded();
    return isPremium.value;
  }

  static Future<int> trialDaysRemaining() async => 0;

  static Future<bool> isTrialExpired() async {
    await _ensureLoaded();
    return !isPremium.value;
  }

  // ── Write ───────────────────────────────────────────────────────────────

  static Future<void> activate({required TierConfig tier}) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;

    await FirebaseFirestore.instance.collection('users').doc(uid).set(
      {
        'isPremium':          true,
        'tier':               tier.firestoreKey,
        'premiumActivatedAt': FieldValue.serverTimestamp(),
      },
      SetOptions(merge: true),
    );

    NotificationService.instance.cancelTrialNudges();
    await _setLocal(true, tier);
  }

  static Future<void> revoke() async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    await FirebaseFirestore.instance.collection('users').doc(uid).set(
      {'isPremium': false, 'tier': 'trial'},
      SetOptions(merge: true),
    );
    await _setLocal(false, TierConfig.trial);
  }

  static Future<bool> checkAndPrompt(BuildContext context) async {
    if (isPremium.value) return true;
    await Navigator.of(context).pushNamed('/paywall');
    return isPremium.value;
  }

  // ── Private ──────────────────────────────────────────────────────────────

  static Future<void> _refreshFromFirestore(String uid) {
    return _refreshOp ??=
        _doRefresh(uid).whenComplete(() => _refreshOp = null);
  }

  static Future<void> _doRefresh(String uid) async {
    try {
      final ref  = FirebaseFirestore.instance.collection('users').doc(uid);
      final doc  = await ref.get();
      final data = doc.data();

      final remote  = data?['isPremium'] as bool?   ?? false;
      final tierKey = data?['tier']      as String? ?? 'trial';

      _loaded = true;
      await _setLocal(remote, TierConfig.fromKey(tierKey));
    } catch (e) {
      debugPrint('PremiumService: Firestore refresh failed — $e');
    }
  }

  static Future<void> _setLocal(bool premium, TierConfig tier) async {
    isPremium.value   = premium;
    currentTier.value = tier;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kIsPremium, premium);
    await prefs.setString(_kTierKey, tier.firestoreKey);
  }
}
