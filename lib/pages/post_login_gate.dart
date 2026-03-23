// lib/pages/post_login_gate.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'home_screen.dart';
import 'onboarding_screen.dart';
import 'package:mindcore_ai/services/daily_motivation_service.dart';

class PostLoginGate extends StatefulWidget {
  const PostLoginGate({super.key});

  @override
  State<PostLoginGate> createState() => _PostLoginGateState();
}

class _PostLoginGateState extends State<PostLoginGate> {
  static const _kOnboardingDone = 'onboarding_done_v1';
  bool? _done;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final done = prefs.getBool(_kOnboardingDone) ?? false;
    if (!mounted) return;

    setState(() => _done = done);

    // ✅ Speak only when the app opens AND onboarding is already completed.
    // This prevents re-speaking when navigating back to Home.
    if (done) {
      await Future.delayed(const Duration(milliseconds: 350));
      await DailyMotivationService.maybeSpeakOnAppOpen(moodLabel: 'neutral');
    }
  }

  Future<void> _finish() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kOnboardingDone, true);

    if (!mounted) return;

    // ✅ Speak once onboarding finishes (still only once per local day due to service).
    await Future.delayed(const Duration(milliseconds: 350));
    await DailyMotivationService.maybeSpeakOnAppOpen(moodLabel: 'neutral');

    // Now proceed normally to Home.
    setState(() => _done = true);
  }

  @override
  Widget build(BuildContext context) {
    final done = _done;
    if (done == null) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (done) return const HomeScreen();
    return OnboardingScreen(onFinish: _finish);
  }
}
