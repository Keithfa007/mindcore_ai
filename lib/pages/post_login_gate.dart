// lib/pages/post_login_gate.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'home_screen.dart';
import 'onboarding_v2_screen.dart';
import 'notification_optin_screen.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/animated_logo.dart';

/// Post-login routing.
///
/// FREEMIUM / TASTE-FIRST MODEL:
/// After onboarding, every user reaches the app. A non-subscribed user gets a
/// small daily free-message allowance (see UsageService.freeDailyMessages).
/// The paywall is now a SOFT upgrade — reached when the free allowance runs
/// out or a paid feature (voice, tools) is opened — not a hard wall on entry.
/// This lets people feel the app help them once before we ever ask for a card.
class PostLoginGate extends StatefulWidget {
  const PostLoginGate({super.key});

  @override
  State<PostLoginGate> createState() => _PostLoginGateState();
}

class _PostLoginGateState extends State<PostLoginGate> {
  static const _kOnboardingDone = 'onboarding_done_v1';
  static const _kNotifOptIn = 'notif_optin_done_v1';

  bool? _onboardingDone;
  bool? _notifOptInDone;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final done  = prefs.getBool(_kOnboardingDone) ?? false;
    final notif = prefs.getBool(_kNotifOptIn) ?? false;

    if (!mounted) return;
    setState(() {
      _onboardingDone = done;
      _notifOptInDone = notif;
    });
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
    if (_onboardingDone == null || _notifOptInDone == null) {
      return const _SplashScreen();
    }

    // Onboarding first — a brand-new user experiences the value and a real AI
    // reply before anything else.
    if (!_onboardingDone!) {
      return OnboardingV2Screen(onFinish: _finish);
    }

    // Ask once about notifications (combined OS permission + daily reminder).
    if (!_notifOptInDone!) {
      return NotificationOptInScreen(onDone: _finishNotif);
    }

    // Everyone — free or subscribed — lands in the app. Usage limits and the
    // paywall handle monetisation from here.
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
