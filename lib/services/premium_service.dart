// lib/services/premium_service.dart
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

  // Trial start is stored PER USER (keyed by uid). It is NEVER device-global,
  // so a brand-new account on a shared device always gets its own fresh trial
  // instead of inheriting a previous account's expired clock.
  static const _kTrialStartPrefix = 'mindcore_trial_start_';

  /// 3-day FREE trial. No payment required.
  static const int _trialDays = 3;

  static bool _initialised = false;

  // Trial state for the CURRENTLY signed-in user.
  static DateTime? _trialStartAt;
  static bool _trialLoaded = false;
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
        _trialStartAt = null;
        _trialLoaded  = false;
        await _setLocal(false, TierConfig.trial);
        return;
      }
      await _refreshFromFirestore(user.uid);
    });
  }

  // ── Trial helpers ──────────────────────────────────────────────────────

  static bool get _trialActive {
    final start = _trialStartAt;
    if (start == null) return true; // unknown: stay permissive during load
    return DateTime.now().difference(start).inHours < (_trialDays * 24);
  }

  /// Ensures trial state for the signed-in user has been loaded at least once.
  static Future<void> _ensureLoaded() async {
    if (_trialLoaded) return;
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    await _refreshFromFirestore(uid);
  }

  /// True if the 3-day trial window is still open.
  static Future<bool> isTrialWindowOpen() async {
    if (isPremium.value) return true;
    await _ensureLoaded();
    return _trialActive;
  }

  /// Days remaining in trial (0 if premium or expired).
  static Future<int> trialDaysRemaining() async {
    if (isPremium.value) return 0;
    await _ensureLoaded();
    final start = _trialStartAt;
    if (start == null) return _trialDays;
    final daysElapsed = DateTime.now().difference(start).inHours ~/ 24;
    return (_trialDays - daysElapsed).clamp(0, _trialDays);
  }

  /// True if the user has had a trial and it is now expired.
  static Future<bool> isTrialExpired() async {
    if (isPremium.value) return false;
    await _ensureLoaded();
    final start = _trialStartAt;
    if (start == null) return false;
    return DateTime.now().difference(start).inHours >= (_trialDays * 24);
  }

  /// User can access the app if subscribed OR within the 3-day trial.
  static Future<bool> hasAccess() async {
    if (isPremium.value) return true;
    await _ensureLoaded();
    // If we still could not resolve a trial start (e.g. offline on a fresh
    // account), stay permissive rather than falsely locking the user out.
    if (!_trialLoaded) return true;
    return _trialActive;
  }

  // ── Trial nudge notifications ───────────────────────────────────────

  static void _scheduleTrialNudges(DateTime trialStart) {
    try {
      NotificationService.instance.scheduleTrialNudges(trialStart);
    } catch (_) {}
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

    // Cancel trial nudges since they subscribed
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
    // Single-flight: prevent concurrent refreshes racing to seed the trial.
    return _refreshOp ??=
        _doRefresh(uid).whenComplete(() => _refreshOp = null);
  }

  static Future<void> _doRefresh(String uid) async {
    final prefs    = await SharedPreferences.getInstance();
    final localKey = '$_kTrialStartPrefix$uid';

    // Seed from any cached per-user value first (offline friendly).
    final cachedRaw = prefs.getString(localKey);
    if (cachedRaw != null) {
      _trialStartAt = DateTime.tryParse(cachedRaw);
      _trialLoaded  = true;
    }

    try {
      final ref  = FirebaseFirestore.instance.collection('users').doc(uid);
      final doc  = await ref.get();
      final data = doc.data();

      final remote  = data?['isPremium'] as bool?   ?? false;
      final tierKey = data?['tier']      as String? ?? 'trial';
      final remoteTrial = data?['trialStartedAt'] as String?;

      if (remoteTrial != null) {
        // Existing account: its own recorded trial start is the source of truth.
        _trialStartAt = DateTime.tryParse(remoteTrial);
        await prefs.setString(localKey, remoteTrial);
      } else {
        // Brand-new account: start a fresh 3-day trial from NOW.
        final nowIso = DateTime.now().toIso8601String();
        _trialStartAt = DateTime.tryParse(nowIso);
        await prefs.setString(localKey, nowIso);
        await ref.set({'trialStartedAt': nowIso}, SetOptions(merge: true));
        final start = _trialStartAt;
        if (start != null) _scheduleTrialNudges(start);
      }

      _trialLoaded = true;
      await _setLocal(remote, TierConfig.fromKey(tierKey));
    } catch (e) {
      debugPrint('PremiumService: Firestore refresh failed — $e');
      // Keep whatever cached value we had; _trialLoaded reflects that.
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
