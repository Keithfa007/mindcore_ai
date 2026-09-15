// lib/pages/email_auth_screen.dart
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';

import '../widgets/page_scaffold.dart';
import '../widgets/glass_card.dart';
import '../services/firebase_auth_service.dart';

import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';

class EmailAuthScreen extends StatefulWidget {
  const EmailAuthScreen({super.key});

  @override
  State<EmailAuthScreen> createState() => _EmailAuthScreenState();
}

class _EmailAuthScreenState extends State<EmailAuthScreen> {
  final _auth = FirebaseAuthService.instance;
  final _emailC = TextEditingController();
  final _passC = TextEditingController();

  bool _isLogin = true;
  bool _loading = false;
  bool _obscure = true;
  String? _error;

  // Forgot-password resend cooldown (prevents spamming reset emails — bug #19).
  bool _resetCooldown = false;
  Timer? _resetTimer;

  @override
  void dispose() {
    _resetTimer?.cancel();
    _emailC.dispose();
    _passC.dispose();
    super.dispose();
  }

  String _friendlyError(Object e) {
    if (e is FirebaseAuthException) {
      switch (e.code) {
        case 'invalid-email':
          return 'That email address doesn’t look right.';
        case 'user-not-found':
          return 'No account found for that email.';
        case 'wrong-password':
        case 'invalid-credential':
          return 'Incorrect email or password.';
        case 'email-already-in-use':
          return 'That email is already registered.';
        case 'weak-password':
          return 'Password is too weak (use at least 6 characters).';
        case 'too-many-requests':
          return 'Too many attempts. Try again in a few minutes.';
        case 'network-request-failed':
          return 'Network error. Check your connection and try again.';
        default:
          return e.message ?? 'Authentication failed.';
      }
    }
    return 'Something went wrong. Please try again.';
  }

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final email = _emailC.text.trim();
      final pass = _passC.text;

      if (email.isEmpty || pass.isEmpty) {
        setState(() => _error = 'Please enter your email and password.');
        return;
      }

      if (pass.contains(' ')) {
        setState(() => _error = 'Password cannot contain spaces.');
        return;
      }

      if (!_isLogin && pass.length < 6) {
        setState(() => _error = 'Password must be at least 6 characters.');
        return;
      }

      if (_isLogin) {
        await _auth.signInWithEmail(email: email, password: pass);
      } else {
        await _auth.signUpWithEmail(email: email, password: pass);
      }

// ✅ Sync down from Firestore now that user is authenticated
      await MoodLogService.syncFromFirestore();
      await JournalService.syncFromFirestore();

      if (!mounted) return;
      // Go straight into the app. Popping only returned to the login screen,
      // which does not listen to auth state, so the user got stuck there.
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (r) => false);
    } catch (e) {
      setState(() => _error = _friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _forgot() async {
    if (_resetCooldown) return;
    final email = _emailC.text.trim();
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email first, then tap “Forgot password?”.');
      return;
    }
    try {
      await _auth.sendPasswordResetEmail(email);
      if (!mounted) return;
      // Clear any stale validation message once the request succeeds (bug #16).
      setState(() {
        _error = null;
        _resetCooldown = true;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reset link sent. Check your inbox (and spam).')),
      );
      // Re-enable after 60s so users can't spam reset emails (bug #19).
      _resetTimer?.cancel();
      _resetTimer = Timer(const Duration(seconds: 60), () {
        if (mounted) setState(() => _resetCooldown = false);
      });
    } catch (e) {
      setState(() => _error = _friendlyError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PageScaffold(
      title: _isLogin ? 'Email Login' : 'Create Account',
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _isLogin ? 'Welcome back' : 'Create your account',
                    style: theme.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _isLogin
                        ? 'Sign in with your email and password.'
                        : 'Use an email + password to save your progress.',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
                      height: 1.25,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),

                  TextField(
                    controller: _emailC,
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.email],
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                  ),
                  const SizedBox(height: 12),

                  TextField(
                    controller: _passC,
                    obscureText: _obscure,
                    autofillHints: const [AutofillHints.password],
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _loading ? null : _submit(),
                    decoration: InputDecoration(
                      labelText: 'Password',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        tooltip: _obscure ? 'Show password' : 'Hide password',
                        onPressed: () => setState(() => _obscure = !_obscure),
                        icon: Icon(
                          _obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 10),

                  if (_error != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      _error!,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.error,
                        height: 1.25,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 6),
                  ],

                  const SizedBox(height: 10),

                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _loading ? null : _submit,
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          _loading
                              ? 'Please wait...'
                              : (_isLogin ? 'Sign in' : 'Create account'),
                        ),
                      ),
                    ),
                  ),

                  const SizedBox(height: 8),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: _loading
                            ? null
                            : () => setState(() {
                          _isLogin = !_isLogin;
                          _error = null;
                        }),
                        child: Text(
                          _isLogin ? 'Create account' : 'I already have an account',
                        ),
                      ),
                      if (_isLogin)
                        TextButton(
                          onPressed: (_loading || _resetCooldown) ? null : _forgot,
                          child: Text(_resetCooldown ? 'Reset link sent' : 'Forgot password?'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
