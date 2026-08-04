// lib/pages/post_login_gate.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'home_screen.dart';
import 'onboarding_v2_screen.dart';
import 'notification_optin_screen.dart';
import 'paywall_screen.dart';
import 'account_sheet.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/services/subscription_service.dart';
import 'package:mindcore_ai/services/firebase_auth_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/animated_logo.dart';

class PostLoginGate extends StatefulWidget {
  const PostLoginGate({super.key});

  @override
  State<PostLoginGate> createState() => _PostLoginGateState();
}

class _PostLoginGateState extends State<PostLoginGate> {
  static const _kOnboardingDone = 'onboarding_done_v1';
  static const _kNotifOptIn = 'notif_optin_done_v1';

  bool? _onboardingDone;
  bool? _hasAccess;
  bool? _notifOptInDone;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final done   = prefs.getBool(_kOnboardingDone) ?? false;
    final notif  = prefs.getBool(_kNotifOptIn) ?? false;
    final access = await PremiumService.hasAccess();

    if (!mounted) return;
    setState(() {
      _onboardingDone = done;
      _notifOptInDone = notif;
      _hasAccess      = access;
    });

    if (done && access) {
      await Future.delayed(const Duration(milliseconds: 350));
    }
  }

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kOnboardingDone, true);
    if (!mounted) return;
    await Future.delayed(const Duration(milliseconds: 350));
    setState(() => _onboardingDone = true);
  }

  Future<void> _finishNotif() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kNotifOptIn, true);
    if (!mounted) return;
    setState(() => _notifOptInDone = true);
  }

  @override
  Widget build(BuildContext context) {
    // Loading — show branded splash instead of plain spinner
    if (_onboardingDone == null ||
        _hasAccess == null ||
        _notifOptInDone == null) {
      return const _SplashScreen();
    }

    // Onboarding now runs BEFORE the access wall, so a brand-new user
    // experiences the value + a real AI reply before ever being asked to pay.
    if (!_onboardingDone!) {
      return OnboardingV2Screen(onFinish: _finish);
    }

    if (!_hasAccess!) {
      return _UnlockScreen(onUnlocked: () async => _load());
    }

    // After the user has access (i.e. after they signed in / started the
    // trial), ask once about notifications — combined OS permission + daily
    // reminder. This is the only place notifications are requested.
    if (!_notifOptInDone!) {
      return NotificationOptInScreen(onDone: _finishNotif);
    }

    return const HomeScreen();
  }
}

// ── Branded splash screen ─────────────────────────────────────────────────

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const AnimatedLogo(size: 150),
              const SizedBox(height: 28),
              Text(
                'MindCore AI',
                style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.8,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'Getting things ready…',
                style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.45),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Unlock screen — starts the 7-day trial directly ────────────────────────
//
// "Start free trial" launches the Google Play 7-day trial offer straight away
// (after linking the anonymous session to a real account). "See all plans"
// opens the full paywall for anyone who wants yearly or Pro.

class _UnlockScreen extends StatefulWidget {
  final VoidCallback onUnlocked;
  const _UnlockScreen({required this.onUnlocked});

  @override
  State<_UnlockScreen> createState() => _UnlockScreenState();
}

class _UnlockScreenState extends State<_UnlockScreen> {
  final _sub = SubscriptionService();
  bool _loading = false;
  bool _ready = false;
  bool _trialAvailable = false;

  @override
  void initState() {
    super.initState();
    PremiumService.isPremium.addListener(_onPremiumChanged);
    _sub.purchaseError.addListener(_onPurchaseError);
    _initStore();
  }

  Future<void> _initStore() async {
    try {
      await _sub.init();
    } catch (e) {
      debugPrint('Unlock: IAP init failed — $e');
    }
    if (!mounted) return;
    setState(() {
      _ready = true;
      _trialAvailable = _sub.hasTrialOffer;
    });
  }

  @override
  void dispose() {
    PremiumService.isPremium.removeListener(_onPremiumChanged);
    _sub.purchaseError.removeListener(_onPurchaseError);
    // NOTE: do not dispose the shared SubscriptionService singleton here — the
    // paywall shares it and manages its own lifecycle.
    super.dispose();
  }

  void _onPremiumChanged() {
    if (PremiumService.isPremium.value && mounted) widget.onUnlocked();
  }

  void _onPurchaseError() {
    final msg = _sub.purchaseError.value;
    if (msg == null || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.red.shade700),
    );
    _sub.purchaseError.value = null;
  }

  Future<void> _startTrial() async {
    // Only ever launch the REAL free-trial offer here. If it did not resolve
    // (account not eligible, offer inactive or still propagating), do NOT
    // silently buy the full-price base plan — send them to the plan chooser.
    final offer = _sub.premiumMonthlyOffer;
    if (offer == null) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
        content: Text(
            'The free trial is not available on this account right now. Here are the plans.'),
      ));
      await _seeAllPlans();
      return;
    }

    // The account step happens HERE — link the anonymous session to a real
    // account before we charge, so the trial and data are recoverable.
    if (FirebaseAuthService.instance.isAnonymous) {
      final ok = await showAccountSheet(context);
      if (ok != true || !mounted) return;
    }

    setState(() => _loading = true);
    try {
      await _sub.buy(offer);
    } catch (e) {
      debugPrint('Unlock: trial buy failed — $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Could not start the trial. $e'),
          backgroundColor: Colors.red.shade700,
        ));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _seeAllPlans() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const PaywallScreen()),
    );
    if (!mounted) return;
    // The paywall disposes the shared purchase stream on close — re-establish
    // it so a subsequent "Start free trial" tap still processes results.
    await _initStore();
    widget.onUnlocked();
  }

  Future<void> _restore() async {
    if (FirebaseAuthService.instance.isAnonymous) {
      final ok = await showAccountSheet(
        context,
        title: 'Sign in to restore',
        subtitle: 'Sign in with the account you subscribed with.',
      );
      if (ok != true || !mounted) return;
    }
    setState(() => _loading = true);
    try {
      await _sub.restore();
    } catch (e) {
      debugPrint('Unlock: restore failed — $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('Could not restore purchases. $e'),
          backgroundColor: Colors.red.shade700,
        ));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    const trialCopy =
        'Start your 7-day free trial to unlock AI chat, voice, guided '
        'sessions and more. A payment method is required, and you can '
        'cancel anytime before day 7 so you are not charged.';
    const subscribeCopy =
        'Subscribe to unlock AI chat, voice, guided sessions and more. '
        'Cancel anytime.';
    // Until the store is ready we optimistically show trial wording.
    final showTrial = !_ready || _trialAvailable;

    return Scaffold(
      backgroundColor: cs.surface,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 40),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Icon(Icons.lock_clock_rounded, size: 64, color: cs.primary),
              const SizedBox(height: 24),
              Text(
                'Unlock MindCore AI',
                style: tt.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                showTrial ? trialCopy : subscribeCopy,
                style: tt.bodyLarge?.copyWith(
                  color: cs.onSurface.withValues(alpha: 0.6),
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              FilledButton(
                onPressed: (!_ready || _loading)
                    ? null
                    : (_trialAvailable ? _startTrial : _seeAllPlans),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14)),
                ),
                child: (!_ready || _loading)
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white))
                    : Text(
                        _trialAvailable
                            ? 'Start 7-day free trial'
                            : 'See all plans',
                        style: tt.titleMedium?.copyWith(color: Colors.white)),
              ),
              if (_ready && _trialAvailable) ...[
                const SizedBox(height: 6),
                TextButton(
                  onPressed: _loading ? null : _seeAllPlans,
                  child: Text(
                    'See all plans',
                    style: tt.bodyMedium?.copyWith(
                        color: cs.primary, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
              TextButton(
                onPressed: _loading ? null : _restore,
                child: Text(
                  'Restore purchases',
                  style: tt.bodyMedium?.copyWith(
                      color: cs.onSurface.withValues(alpha: 0.45)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
