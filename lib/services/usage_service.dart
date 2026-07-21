// lib/services/usage_service.dart
//
// Tracks message + voice usage per billing period.
// Trial users get daily limits (15 msgs/day, 5 min voice/day).
// Paid users get monthly limits from their tier.
// bonusVoiceSeconds (purchased voice packs) lives on the USER document
// so it is NEVER wiped at month rollover.

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class UsageSnapshot {
  final int messagesUsed;
  final int voiceSecondsUsed;
  final int bonusVoiceSeconds;
  final TierConfig tier;

  const UsageSnapshot({
    required this.messagesUsed,
    required this.voiceSecondsUsed,
    required this.tier,
    this.bonusVoiceSeconds = 0,
  });

  static const empty = UsageSnapshot(
    messagesUsed: 0, voiceSecondsUsed: 0, tier: TierConfig.trial,
  );

  int get messagesRemaining {
    if (tier.isUnlimited) return 9999;
    return (tier.monthlyMessages - messagesUsed).clamp(0, tier.monthlyMessages);
  }

  int get totalVoiceSeconds => tier.monthlyVoiceSeconds + bonusVoiceSeconds;

  int get voiceSecondsRemaining {
    if (tier.monthlyVoiceSeconds == -1) return 9999;
    return (totalVoiceSeconds - voiceSecondsUsed).clamp(0, totalVoiceSeconds);
  }

  int get voiceMinutesRemaining => (voiceSecondsRemaining / 60).floor();

  bool get canSendMessage =>
      tier.isUnlimited || messagesUsed < tier.monthlyMessages;

  bool get canUseVoice =>
      tier.hasVoice &&
      (tier.monthlyVoiceSeconds == -1 || voiceSecondsUsed < totalVoiceSeconds);

  double get messageFraction {
    if (tier.isUnlimited) return 0;
    return (messagesUsed / tier.monthlyMessages).clamp(0.0, 1.0);
  }

  double get voiceFraction {
    if (totalVoiceSeconds <= 0) return 0;
    return (voiceSecondsUsed / totalVoiceSeconds).clamp(0.0, 1.0);
  }

  UsageSnapshot copyWith({
    int? messagesUsed, int? voiceSecondsUsed,
    int? bonusVoiceSeconds, TierConfig? tier,
  }) => UsageSnapshot(
    messagesUsed:      messagesUsed      ?? this.messagesUsed,
    voiceSecondsUsed:  voiceSecondsUsed  ?? this.voiceSecondsUsed,
    bonusVoiceSeconds: bonusVoiceSeconds ?? this.bonusVoiceSeconds,
    tier:              tier              ?? this.tier,
  );
}

class UsageService {
  UsageService._();
  static final UsageService instance = UsageService._();

  final snapshot = ValueNotifier<UsageSnapshot>(UsageSnapshot.empty);

  // Period-scoped keys (reset monthly)
  static const _kMsgs   = 'usage_msgs_';
  static const _kVoice  = 'usage_voice_';
  static const _kPeriod = 'usage_period';
  static const _kTier   = 'usage_tier';
  static const _kBonus  = 'usage_bonus_voice_total';

  // Trial daily keys (reset daily)
  static const _kTrialDailyMsgs  = 'trial_daily_msgs_';
  static const _kTrialDailyVoice = 'trial_daily_voice_';

  bool _initialised = false;
  int  _voiceBuffer = 0;

  bool get _isTrialUser => PremiumService.currentTier.value.isTrial;

  String get _todayKey {
    final d = DateTime.now();
    return '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  }

  Future<void> init() async {
    if (_initialised) return;
    _initialised = true;
    await _loadFromCache();
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) await _syncFromFirestore(user.uid);
    FirebaseAuth.instance.authStateChanges().listen((user) async {
      if (user == null) { snapshot.value = UsageSnapshot.empty; return; }
      await _syncFromFirestore(user.uid);
    });
    PremiumService.isPremium.addListener(() async {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) await _syncFromFirestore(user.uid);
    });
  }

  // ── Trial daily usage helpers ─────────────────────────────────────────

  Future<int> _trialDailyMsgsUsed() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt('$_kTrialDailyMsgs$_todayKey') ?? 0;
  }

  Future<void> _incrementTrialDailyMsgs() async {
    final prefs = await SharedPreferences.getInstance();
    final current = prefs.getInt('$_kTrialDailyMsgs$_todayKey') ?? 0;
    await prefs.setInt('$_kTrialDailyMsgs$_todayKey', current + 1);
  }

  Future<int> _trialDailyVoiceUsed() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt('$_kTrialDailyVoice$_todayKey') ?? 0;
  }

  Future<void> _incrementTrialDailyVoice(int seconds) async {
    final prefs = await SharedPreferences.getInstance();
    final current = prefs.getInt('$_kTrialDailyVoice$_todayKey') ?? 0;
    await prefs.setInt('$_kTrialDailyVoice$_todayKey', current + seconds);
  }

  // ── Message gating ───────────────────────────────────────────────────

  Future<bool> tryConsumeMessage(BuildContext context) async {
    // Chat requires an active trial or a paid subscription (same rule as voice).
    // Anyone whose trial has ended and who is not subscribed is blocked here.
    if (!PremiumService.isPremium.value) {
      final hasAccess = await PremiumService.hasAccess();
      if (!hasAccess) {
        await _showLimitDialog(context,
          title: 'Your free trial has ended',
          body: 'You had 3 days of full access. Subscribe to keep chatting, '
              'and your conversations and progress stay saved.',
        );
        return false;
      }
    }

    // Trial users: enforce daily limits
    if (_isTrialUser) {
      final dailyUsed = await _trialDailyMsgsUsed();
      final dailyLimit = TierConfig.trial.trialDailyMessages;
      if (dailyUsed >= dailyLimit) {
        final remaining = await PremiumService.trialDaysRemaining();
        await _showLimitDialog(context,
          title: 'Daily limit reached',
          body: 'You\'ve used all $dailyLimit messages for today.\n\n'
              '${remaining > 0 ? 'You have $remaining day${remaining == 1 ? '' : 's'} left in your free trial. Come back tomorrow or subscribe now.' : 'Subscribe to unlock full access.'}',
        );
        return false;
      }

      await _incrementTrialDailyMsgs();
    }

    final snap = snapshot.value;
    if (!_isTrialUser && !snap.canSendMessage) {
      await _showLimitDialog(context,
        title: 'Message limit reached',
        body: 'You\'ve used all ${snap.tier.monthlyMessages} messages '
            'for this month on the ${snap.tier.displayName} plan.\n\n'
            'Upgrade to send more.',
      );
      return false;
    }

    final updated = snap.copyWith(messagesUsed: snap.messagesUsed + 1);
    snapshot.value = updated;
    await _persistLocally(updated);
    _incrementPeriodFirestore('messagesUsed', 1);
    return true;
  }

  // ── Voice gating ─────────────────────────────────────────────────────

  Future<bool> tryConsumeVoice(BuildContext context) async {
    final snap = snapshot.value;

    if (!snap.tier.hasVoice) {
      await _showLimitDialog(context,
        title: 'Voice not included',
        body: 'Hands-free voice is available on Premium and Pro plans.',
      );
      return false;
    }

    // Trial users: check daily voice limit
    if (_isTrialUser) {
      final expired = await PremiumService.isTrialExpired();
      if (expired) {
        await _showLimitDialog(context,
          title: 'Your free trial has ended',
          body: 'Subscribe to keep using voice chat.',
        );
        return false;
      }

      final dailyUsed  = await _trialDailyVoiceUsed();
      final dailyLimit = TierConfig.trial.trialDailyVoiceSeconds;
      if (dailyUsed >= dailyLimit) {
        await _showLimitDialog(context,
          title: 'Voice limit for today',
          body: 'You\'ve used your 5 minutes of voice for today.\n\n'
              'Come back tomorrow or subscribe for more.',
        );
        return false;
      }
    }

    if (!_isTrialUser && !snap.canUseVoice) {
      await _showLimitDialog(context,
        title: 'Voice minutes used up',
        body: 'You\'ve used all your voice minutes this month.\n\n'
            'Buy a voice top-up pack or upgrade your plan.',
      );
      return false;
    }

    return true;
  }

  Future<bool> recordVoiceSecond() async {
    final snap = snapshot.value;

    // Trial daily voice tracking
    if (_isTrialUser) {
      final dailyUsed  = await _trialDailyVoiceUsed();
      final dailyLimit = TierConfig.trial.trialDailyVoiceSeconds;
      if (dailyUsed >= dailyLimit) return false;
      await _incrementTrialDailyVoice(1);
    }

    if (!_isTrialUser && !snap.canUseVoice) return false;

    final updated = snap.copyWith(voiceSecondsUsed: snap.voiceSecondsUsed + 1);
    snapshot.value = updated;

    _voiceBuffer++;
    if (_voiceBuffer >= 10) {
      _incrementPeriodFirestore('voiceSecondsUsed', _voiceBuffer);
      _voiceBuffer = 0;
    }

    return true;
  }

  // ── Voice pack top-up ─────────────────────────────────────────────────

  Future<void> addVoiceMinutes(int minutes) async {
    final addSeconds = minutes * 60;
    final updated = snapshot.value.copyWith(
      bonusVoiceSeconds: snapshot.value.bonusVoiceSeconds + addSeconds,
    );
    snapshot.value = updated;
    await _persistLocally(updated);
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid != null) {
      try {
        await FirebaseFirestore.instance.collection('users').doc(uid).set({
          'bonusVoiceSeconds': FieldValue.increment(addSeconds),
          'bonusUpdatedAt':    FieldValue.serverTimestamp(),
        }, SetOptions(merge: true));
      } catch (e) {
        debugPrint('UsageService: addVoiceMinutes Firestore failed — $e');
      }
    }
    debugPrint('UsageService: added $minutes voice minutes (+${addSeconds}s)');
  }

  Future<void> flushVoiceBuffer() async {
    if (_voiceBuffer > 0) {
      await _incrementPeriodFirestore('voiceSecondsUsed', _voiceBuffer);
      _voiceBuffer = 0;
    }
    await _persistLocally(snapshot.value);
  }

  // ── Firestore sync ─────────────────────────────────────────────────────

  Future<void> _syncFromFirestore(String uid) async {
    final period     = _currentPeriod();
    final tierConfig = PremiumService.currentTier.value;
    try {
      final periodRef = FirebaseFirestore.instance
          .collection('users').doc(uid).collection('usage').doc(period);
      final userRef = FirebaseFirestore.instance.collection('users').doc(uid);
      final results = await Future.wait([periodRef.get(), userRef.get()]);
      final periodDoc = results[0];
      final userDoc   = results[1];
      int msgs   = 0;
      int voices = 0;
      final int bonus = (userDoc.data()?['bonusVoiceSeconds'] as int?) ?? 0;
      if (periodDoc.exists) {
        msgs   = (periodDoc.data()?['messagesUsed']    as int?) ?? 0;
        voices = (periodDoc.data()?['voiceSecondsUsed'] as int?) ?? 0;
      } else {
        await periodDoc.reference.set({
          'messagesUsed': 0, 'voiceSecondsUsed': 0,
          'tier': tierConfig.firestoreKey,
          'periodStart': FieldValue.serverTimestamp(),
          'updatedAt':   FieldValue.serverTimestamp(),
        });
      }
      final updated = UsageSnapshot(
        messagesUsed: msgs, voiceSecondsUsed: voices,
        bonusVoiceSeconds: bonus, tier: tierConfig,
      );
      snapshot.value = updated;
      await _persistLocally(updated);
    } catch (e) {
      debugPrint('UsageService: Firestore sync failed — $e');
    }
  }

  Future<void> _incrementPeriodFirestore(String field, int amount) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    try {
      await FirebaseFirestore.instance
          .collection('users').doc(uid)
          .collection('usage').doc(_currentPeriod())
          .set({
        field:       FieldValue.increment(amount),
        'updatedAt': FieldValue.serverTimestamp(),
        'tier':      PremiumService.currentTier.value.firestoreKey,
      }, SetOptions(merge: true));
    } catch (e) {
      debugPrint('UsageService: increment failed — $e');
    }
  }

  // ── Local cache ─────────────────────────────────────────────────────────

  Future<void> _loadFromCache() async {
    final prefs  = await SharedPreferences.getInstance();
    final period = _currentPeriod();
    final cached = prefs.getString(_kPeriod);
    if (cached != null && cached != period) {
      await prefs.remove(_kMsgs  + cached);
      await prefs.remove(_kVoice + cached);
      await prefs.setString(_kPeriod, period);
    }
    final msgs   = prefs.getInt(_kMsgs  + period) ?? 0;
    final voices = prefs.getInt(_kVoice + period) ?? 0;
    final bonus  = prefs.getInt(_kBonus)           ?? 0;
    final tier   = TierConfig.fromKey(prefs.getString(_kTier));
    snapshot.value = UsageSnapshot(
      messagesUsed: msgs, voiceSecondsUsed: voices,
      bonusVoiceSeconds: bonus, tier: tier,
    );
  }

  Future<void> _persistLocally(UsageSnapshot snap) async {
    final prefs  = await SharedPreferences.getInstance();
    final period = _currentPeriod();
    await prefs.setString(_kPeriod, period);
    await prefs.setInt(_kMsgs  + period, snap.messagesUsed);
    await prefs.setInt(_kVoice + period, snap.voiceSecondsUsed);
    await prefs.setInt(_kBonus, snap.bonusVoiceSeconds);
    await prefs.setString(_kTier, snap.tier.firestoreKey);
  }

  String _currentPeriod() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}';
  }

  // ── Limit dialog ───────────────────────────────────────────────────────

  Future<void> _showLimitDialog(
    BuildContext context, {
    required String title,
    required String body,
  }) async {
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title:   Text(title),
        content: Text(body),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Not now')),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pushNamed('/paywall');
            },
            child: const Text('See plans'),
          ),
        ],
      ),
    );
  }
}
