// lib/services/premium_service.dart
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/models/tier_config.dart';

class PremiumService {
  PremiumService._();

  static final isPremium   = ValueNotifier<bool>(false);
  static final currentTier = ValueNotifier<TierConfig>(TierConfig.trial);

  static const _kIsPremium  = 'mindcore_is_premium';
  static const _kTierKey    = 'mindcore_tier_key';
  static const _kTrialStart = 'mindcore_trial_start';

  // Trial is 7 days at €1.99 (one-time purchase)
  static const int _trialDays = 7;

  static bool _initialised = false;

  // ── Init ──────────────────────────────────────────────────────────────

  static Future<void> init() async {
    if (_initialised) return;
    _initialised = true;

    final prefs = await SharedPreferences.getInstance();

    // Record trial start on very first launch (local)
    final trialStartRaw = prefs.getString(_kTrialStart);
    if (trialStartRaw == null) {
      final now = DateTime.now().toIso8601String();
      await prefs.setString(_kTrialStart, now);
    }

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

  // ── Trial helpers ─────────────────────────────────────────────────────

  /// True if the 7-day trial window is still open.
  static Future<bool> isTrialWindowOpen() async {
    if (isPremium.value) return true;
    final start = await _trialStart();
    if (start == null) return true;
    return DateTime.now().difference(start).inDays < _trialDays;
  }

  /// Days remaining in trial (0 if premium or expired).
  static Future<int> trialDaysRemaining() async {
    if (isPremium.value) return 0;
    final start = await _trialStart();
    if (start == null) return _trialDays;
    final elapsed = DateTime.now().difference(start).inDays;
    return (_trialDays - elapsed).clamp(0, _trialDays);
  }

  /// User can access the app if subscribed OR within the 7-day trial window.
  static Future<bool> hasAccess() async {
    if (isPremium.value) return true;
    return isTrialWindowOpen();
  }

  // ── Write ──────────────────────────────────────────────────────────────

  static Future<void> activate({required TierConfig tier}) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;

    final prefs       = await SharedPreferences.getInstance();
    final trialStart  = prefs.getString(_kTrialStart) ??
        DateTime.now().toIso8601String();

    await FirebaseFirestore.instance.collection('users').doc(uid).set(
      {
        'isPremium':          true,
        'tier':               tier.firestoreKey,
        'premiumActivatedAt': FieldValue.serverTimestamp(),
        // Persist trial start to Firestore so reinstalls don’t reset it
        'trialStartedAt':     trialStart,
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

  static Future<bool> checkAndPrompt(BuildContext context) async {
    if (isPremium.value) return true;
    await Navigator.of(context).pushNamed('/paywall');
    return isPremium.value;
  }

  // ── Private ───────────────────────────────────────────────────────────

  static Future<void> _refreshFromFirestore(String uid) async {
    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .get();

      final data      = doc.data();
      final remote    = data?['isPremium']   as bool?   ?? false;
      final tierKey   = data?['tier']        as String? ?? 'trial';

      // Restore trial start from Firestore if present (survives reinstall)
      final remoteTrial = data?['trialStartedAt'] as String?;
      if (remoteTrial != null) {
        final prefs = await SharedPreferences.getInstance();
        final local = prefs.getString(_kTrialStart);
        // Only restore if local is missing or Firestore has an earlier date
        if (local == null) {
          await prefs.setString(_kTrialStart, remoteTrial);
        } else {
          final localDt  = DateTime.tryParse(local);
          final remoteDt = DateTime.tryParse(remoteTrial);
          if (localDt != null &&
              remoteDt != null &&
              remoteDt.isBefore(localDt)) {
            await prefs.setString(_kTrialStart, remoteTrial);
          }
        }
      } else {
        // First login: push local trial start to Firestore so it’s preserved
        final prefs      = await SharedPreferences.getInstance();
        final localTrial = prefs.getString(_kTrialStart);
        if (localTrial != null) {
          await FirebaseFirestore.instance
              .collection('users')
              .doc(uid)
              .set({'trialStartedAt': localTrial}, SetOptions(merge: true));
        }
      }

      await _setLocal(remote, TierConfig.fromKey(tierKey));
    } catch (e) {
      debugPrint('PremiumService: Firestore refresh failed — $e');
    }
  }

  static Future<DateTime?> _trialStart() async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(_kTrialStart);
    if (raw == null) return null;
    return DateTime.tryParse(raw);
  }

  static Future<void> _setLocal(bool premium, TierConfig tier) async {
    isPremium.value   = premium;
    currentTier.value = tier;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kIsPremium, premium);
    await prefs.setString(_kTierKey, tier.firestoreKey);
  }
}
