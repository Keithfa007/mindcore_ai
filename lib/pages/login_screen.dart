// lib/pages/login_screen.dart
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';

import 'email_auth_screen.dart';
import '../services/firebase_auth_service.dart';
import '../services/mood_log_service.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  bool _initDone = false;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _ensureFirebase();
  }

  Future<void> _ensureFirebase() async {
    try {
      await Firebase.initializeApp();
      setState(() => _initDone = true);
    } catch (e) {
      setState(() {
        _error = 'Firebase init failed: $e';
        _initDone = true;
      });
    }
  }

  Future<void> _googleSignIn() async {
    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      // 1️⃣ Sign in
      await FirebaseAuthService.instance.signInWithGoogle();

      // 2️⃣ Sync moods from Firestore → local cache
      await MoodLogService.syncFromFirestore();

      // 2️⃣ Sync journal from Firestore → local cache
      await JournalService.syncFromFirestore();

      if (!mounted) return;

      // 3️⃣ Go to home
      Navigator.of(context).pushReplacementNamed('/home');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Logo
                  Opacity(
                    opacity: 0.95,
                    child: Image.asset(
                      'assets/images/logo512.png',
                      height: 120,
                      fit: BoxFit.contain,
                    ),
                  ),
                  const SizedBox(height: 16),

                  // App name
                  Text(
                    'MindCore AI',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0.2,
                    ),
                  ),
                  const SizedBox(height: 8),

                  // Subtitle
                  Text(
                    'Sign in to continue',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyLarge?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.75),
                    ),
                  ),
                  const SizedBox(height: 24),

                  if (!_initDone) ...[
                    const Center(child: CircularProgressIndicator()),
                  ] else ...[
                    if (_error != null) ...[
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: theme.colorScheme.errorContainer,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          _error!,
                          style: TextStyle(color: theme.colorScheme.onErrorContainer),
                        ),
                      ),
                      const SizedBox(height: 16),
                    ],

                    FilledButton.icon(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const EmailAuthScreen()),
                      ),
                      icon: const Icon(Icons.mail_outline),
                      label: const Text('Continue with Email'),
                    ),

                    FilledButton.icon(
                      onPressed: _busy ? null : _googleSignIn,
                      icon: const Icon(Icons.login),
                      label: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12.0),
                        child: Text(_busy ? 'Signing in...' : 'Continue with Google'),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
