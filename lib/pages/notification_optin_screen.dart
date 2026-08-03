// lib/pages/notification_optin_screen.dart
//
// One combined notification opt-in, shown AFTER the user has an account and
// access (i.e. after they start the trial / sign in) — never during onboarding.
// It merges the two old prompts: the in-app daily reminder and the OS
// notification permission. The Android system permission dialog is only
// triggered if the user taps "Yes", so it never appears unprompted.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/settings_service.dart';

class NotificationOptInScreen extends StatefulWidget {
  final VoidCallback onDone;
  const NotificationOptInScreen({super.key, required this.onDone});

  @override
  State<NotificationOptInScreen> createState() =>
      _NotificationOptInScreenState();
}

class _NotificationOptInScreenState extends State<NotificationOptInScreen> {
  bool _busy = false;

  Future<void> _choose(bool enable) async {
    if (_busy) return;
    setState(() => _busy = true);
    HapticFeedback.lightImpact();
    try {
      await SettingsService.setDailyReminderEnabled(enable);
      if (enable) {
        // Only now — after an explicit opt-in — request the OS permission.
        await FirebaseMessaging.instance.requestPermission(
          alert: true,
          badge: true,
          sound: true,
        );
      }
    } catch (_) {
      // Best effort — never block entry to the app.
    }
    if (!mounted) return;
    widget.onDone();
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final subtle = isDark
        ? Colors.white.withValues(alpha: 0.60)
        : const Color(0xFF475467);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              children: [
                const Spacer(),
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.primary.withValues(alpha: 0.12),
                    border: Border.all(
                        color: AppColors.primary.withValues(alpha: 0.30),
                        width: 1.5),
                  ),
                  child: Icon(Icons.notifications_rounded,
                      color: AppColors.primary, size: 38),
                ),
                const SizedBox(height: 26),
                Text('Stay connected to yourself',
                    textAlign: TextAlign.center,
                    style: tt.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.6,
                        color:
                            isDark ? Colors.white : const Color(0xFF0E1320))),
                const SizedBox(height: 12),
                Text(
                  'Would you like a gentle daily reminder to check in, plus the '
                  'occasional helpful update? Just a light touch, at a time that '
                  'suits you.',
                  textAlign: TextAlign.center,
                  style: tt.bodyMedium?.copyWith(color: subtle, height: 1.5),
                ),
                const Spacer(),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _busy ? null : () => _choose(true),
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      disabledBackgroundColor:
                          AppColors.primary.withValues(alpha: 0.4),
                      minimumSize: const Size.fromHeight(54),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(16)),
                    ),
                    child: _busy
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white))
                        : const Text('Yes, keep me in touch',
                            style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w800,
                                fontSize: 15)),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: _busy ? null : () => _choose(false),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(54),
                      side: BorderSide(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.20)
                            : Colors.black.withValues(alpha: 0.15),
                      ),
                    ),
                    child: Text('Not right now',
                        style: TextStyle(color: subtle)),
                  ),
                ),
                const SizedBox(height: 32),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
