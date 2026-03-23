// lib/services/usage_service.dart
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
  final TierConfig tier;

  const UsageSnapshot({
    required this.messagesUsed,
    required this.voiceSecondsUsed,
    required this.tier,
  });

  static const empty = UsageSnapshot(
    messagesUsed: 0,
    voiceSecondsUsed: 0,
    tier: TierConfig.trial,
  );

  int get messagesRemaining {
    if (tier.isUnlimited) return 9999;
    return (tier.monthlyMessages - messagesUsed).clamp(0, tier.monthlyMessages);
  }

  int get voiceSecondsRemaining {
    if (tier.monthlyVoiceSeconds == -1) return 9999;
    return (tier.monthlyVoiceSeconds - voiceSecondsUsed)
        .clamp(0, tier.monthlyVoiceSeconds);
  }

  int get voiceMinutesRemaining => (voiceSecondsRemaining / 60).floor();

  bool get canSendMessage =>
      tier.isUnlimited || messagesUsed < tier.monthlyMessages;

  bool get canUseVoice =>
      tier.hasVoice &&
      (tier.monthlyVoiceSeconds == -1 ||
          voiceSecondsUsed < tier.monthlyVoiceSeconds);

  double get messageFraction {
    if (tier.isUnlimited) return 0;
    return (messagesUsed / tier.monthlyMessages).clamp(0.0, 1.0);
  }

  double get voiceFraction {
    if (tier.monthlyVoiceSeconds <= 0) return 0;
    return (voiceSecondsUsed / tier.monthlyVoiceSeconds).clamp(0.0, 1.0);
  }

  UsageSnapshot copyWith({
    int? messagesUsed,
    int? voiceSecondsUsed,
    TierConfig? tier,
  }) {
    return UsageSnapshot(
      messagesUsed: messagesUsed ?? this.messagesUsed,
      voiceSecondsUsed: voiceSecondsUsed ?? this.voiceSecondsUsed,
      tier: tier ?? this.tier,
    );
  }
}

class UsageService {
  UsageService._();
  static final UsageService instance = UsageService._();

  final snapshot = ValueNotifier<UsageSnapshot>(UsageSnapshot.empty);

  static const _kMsgs   = 'usage_msgs_';
  static const _kVoice  = 'usage_voice_';
  static const _kPeriod = 'usage_period';
  static const _kTier   = 'usage_tier';

  bool _initialised = false;
  int _voiceBuffer = 0;

  Future<void> init() async {
    if (_initialised) return;
    _initialised = true;

    await _loadFromCache();

    FirebaseAuth.instance.authStateChanges().listen((user) async {
      if (user == null) {
        snapshot.value = UsageSnapshot.empty;
        return;
      }
      await _syncFromFirestore(user.uid);
    });

    PremiumService.isPremium.addListener(() async {
      final user = FirebaseAuth.instance.currentUser;
      if (user != null) await _syncFromFirestore(user.uid);
    });
  }

  Future<bool> tryConsumeMessage(BuildContext context) async {
    final snap = snapshot.value;

    if (!snap.canSendMessage) {
      await _showLimitDialog(
        context,
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
    _incrementFirestore('messagesUsed', 1);
    return true;
  }

  Future<bool> tryConsumeVoice(BuildContext context) async {
    final snap = snapshot.value;

    if (!snap.tier.hasVoice) {
      await _showLimitDialog(
        context,
        title: 'Voice not included',
        body: 'Hands-free voice is available on Premium and Pro plans.',
      );
      return false;
    }

    if (!snap.canUseVoice) {
      await _showLimitDialog(
        context,
        title: 'Voice minutes used up',
        body: 'You\'ve used all ${snap.tier.voiceMinutes} voice minutes '
            'for this month on the ${snap.tier.displayName} plan.\n\n'
            'Upgrade to Pro for more.',
      );
      return false;
    }

    return true;
  }

  Future<bool> recordVoiceSecond() async {
    final snap = snapshot.value;
    if (!snap.canUseVoice) return false;

    final updated = snap.copyWith(
      voiceSecondsUsed: snap.voiceSecondsUsed + 1,
    );
    snapshot.value = updated;

    _voiceBuffer++;
    if (_voiceBuffer >= 10) {
      _incrementFirestore('voiceSecondsUsed', _voiceBuffer);
      _voiceBuffer = 0;
    }

    return updated.canUseVoice;
  }

  Future<void> flushVoiceBuffer() async {
    if (_voiceBuffer > 0) {
      await _incrementFirestore('voiceSecondsUsed', _voiceBuffer);
      _voiceBuffer = 0;
    }
    await _persistLocally(snapshot.value);
  }

  Future<void> _syncFromFirestore(String uid) async {
    final period = _currentPeriod();
    final tierConfig = PremiumService.currentTier.value;

    try {
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('usage')
          .doc(period)
          .get();

      int msgs   = 0;
      int voices = 0;

      if (doc.exists) {
        msgs   = (doc.data()?['messagesUsed']     as int?) ?? 0;
        voices = (doc.data()?['voiceSecondsUsed'] as int?) ?? 0;
      } else {
        await doc.reference.set({
          'messagesUsed':     0,
          'voiceSecondsUsed': 0,
          'tier':             tierConfig.firestoreKey,
          'periodStart':      FieldValue.serverTimestamp(),
          'updatedAt':        FieldValue.serverTimestamp(),
        });
      }

      final updated = UsageSnapshot(
        messagesUsed:     msgs,
        voiceSecondsUsed: voices,
        tier:             tierConfig,
      );

      snapshot.value = updated;
      await _persistLocally(updated);
    } catch (e) {
      debugPrint('UsageService: Firestore sync failed — $e');
    }
  }

  Future<void> _incrementFirestore(String field, int amount) async {
    final uid = FirebaseAuth.instance.currentUser?.uid;
    if (uid == null) return;
    try {
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('usage')
          .doc(_currentPeriod())
          .set(
        {
          field:       FieldValue.increment(amount),
          'updatedAt': FieldValue.serverTimestamp(),
          'tier':      PremiumService.currentTier.value.firestoreKey,
        },
        SetOptions(merge: true),
      );
    } catch (e) {
      debugPrint('UsageService: increment failed — $e');
    }
  }

  Future<void> _loadFromCache() async {
    final prefs  = await SharedPreferences.getInstance();
    final period = _currentPeriod();
    final cached = prefs.getString(_kPeriod);

    if (cached != null && cached != period) {
      await prefs.remove(_kMsgs + cached);
      await prefs.remove(_kVoice + cached);
      await prefs.setString(_kPeriod, period);
    }

    final msgs   = prefs.getInt(_kMsgs + period)  ?? 0;
    final voices = prefs.getInt(_kVoice + period)  ?? 0;
    final tier   = TierConfig.fromKey(prefs.getString(_kTier));

    snapshot.value = UsageSnapshot(
      messagesUsed:     msgs,
      voiceSecondsUsed: voices,
      tier:             tier,
    );
  }

  Future<void> _persistLocally(UsageSnapshot snap) async {
    final prefs  = await SharedPreferences.getInstance();
    final period = _currentPeriod();
    await prefs.setString(_kPeriod, period);
    await prefs.setInt(_kMsgs   + period, snap.messagesUsed);
    await prefs.setInt(_kVoice  + period, snap.voiceSecondsUsed);
    await prefs.setString(_kTier, snap.tier.firestoreKey);
  }

  String _currentPeriod() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}';
  }

  Future<void> _showLimitDialog(
    BuildContext context, {
    required String title,
    required String body,
  }) async {
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Not now'),
          ),
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