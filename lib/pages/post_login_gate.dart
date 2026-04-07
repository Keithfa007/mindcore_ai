// lib/pages/post_login_gate.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'paywall_screen.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/animated_logo.dart';

class PostLoginGate extends StatefulWidget {
  const PostLoginGate({super.key});

  @override
  State<PostLoginGate> createState() => _PostLoginGateState();
}

class _PostLoginGateState extends State<PostLoginGate> {
  static const _kOnboardingDone = 'onboarding_done_v1';

  bool? _onboardingDone;
  bool? _hasAccess;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    //await prefs.remove('onboarding_done_v1'); // TEMP — delete after testing
    final done   = prefs.getBool(_kOnboardingDone) ?? false;
    final access = await PremiumService.hasAccess();

    if (!mounted) return;
    setState(() {
      _onboardingDone = done;
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

  @override
  Widget build(BuildContext context) {
    // Loading — show branded splash instead of plain spinner
    if (_onboardingDone == null || _hasAccess == null) {
      return const _SplashScreen();
    }

    if (!_hasAccess!) {
      return _TrialExpiredScreen(onSubscribe: () async => _load());
    }

    if (!_onboardingDone!) {
      return OnboardingScreen(onFinish: _finish);
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

// ── Trial expired screen ───────────────────────────────────────────────────

class _TrialExpiredScreen extends StatelessWidget {
  final VoidCallback onSubscribe;
  const _TrialExpiredScreen({required this.onSubscribe});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

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
                'Your free trial has ended',
                style: tt.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 12),
              Text(
                'Your 30-day trial has expired. Subscribe to keep '
                'your progress, conversations and wellness journey going.',
                style: tt.bodyLarge?.copyWith(
                  color: cs.onSurface.withValues(alpha: 0.6),
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              FilledButton(
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PaywallScreen()),
                  );
                  onSubscribe();
                },
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14)),
                ),
                child: Text('See plans',
                    style: tt.titleMedium?.copyWith(color: Colors.white)),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () async {
                  await Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const PaywallScreen()),
                  );
                  onSubscribe();
                },
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
