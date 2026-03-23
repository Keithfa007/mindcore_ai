// lib/services/premium_service.dart
import 'package:flutter/foundation.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/models/tier_config.dart';

class PremiumService {
  PremiumService._();

  static final isPremium = ValueNotifier<bool>(false);
  static final currentTier = ValueNotifier<TierConfig>(TierConfig.trial);

  static const _kIsPremium = 'mindcore_is_premium';
  static const _kTierKey   = 'mindcore_tier_key';
  static bool _initialised = false;

  static Future<void> init() async {
    if (_initialised) return;
    _initialised = true;

    final prefs = await SharedPreferences.getInstance();
    isPremium.value   = prefs.getBool(_kIsPremium) ?? false;
    currentTier.value = TierConfig.fromKey(prefs.getString(_kTierKey));

    FirebaseAuth.instance.authStateChanges().listen((user) async {
      if (user == null) {
        await _setLocal(false, TierConfig.trial);
        return;
      }
      await _refreshFromFirestore(user.uid);
    });
  }

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

  static Future<bool> checkAndPrompt(context) async {
    if (isPremium.value) return true;
    await Navigator.of(context).pushNamed('/paywall');
    return isPremium.value;
  }

  static Future<void> _refreshFromFirestore(String uid) async {
    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .get();

      final remote  = doc.data()?['isPremium'] as bool?   ?? false;
      final tierKey = doc.data()?['tier']      as String? ?? 'trial';
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