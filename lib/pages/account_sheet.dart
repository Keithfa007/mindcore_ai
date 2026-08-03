// lib/pages/account_sheet.dart
//
// A sign-in sheet shown at the "Start free trial" / restore moment. It links
// the current anonymous session to a real Google or email account (or signs
// into an existing one), so the account step comes AFTER the user has seen the
// value, not before. Returns true when the user ends up signed in with a real
// account, and null/false if they dismissed it.
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';

import 'package:mindcore_ai/services/firebase_auth_service.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

Future<bool?> showAccountSheet(
  BuildContext context, {
  String title = 'Create your account',
  String subtitle =
      'Save your progress and start your free trial. Cancel anytime.',
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _AccountSheet(title: title, subtitle: subtitle),
  );
}

class _AccountSheet extends StatefulWidget {
  final String title;
  final String subtitle;
  const _AccountSheet({required this.title, required this.subtitle});

  @override
  State<_AccountSheet> createState() => _AccountSheetState();
}

class _AccountSheetState extends State<_AccountSheet> {
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  bool _busy = false;
  bool _showEmail = false;
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _google() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await FirebaseAuthService.instance.linkOrSignInWithGoogle();
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on FirebaseAuthException catch (e) {
      if (e.code == 'google-sign-in-cancelled') {
        if (mounted) setState(() => _busy = false);
        return;
      }
      if (mounted) {
        setState(() {
          _error = _friendly(e);
          _busy = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Something went wrong. Please try again.';
          _busy = false;
        });
      }
    }
  }

  Future<void> _email() async {
    final email = _emailCtrl.text.trim();
    final pass = _passCtrl.text;
    if (email.isEmpty || !email.contains('@')) {
      setState(() => _error = 'Enter a valid email address.');
      return;
    }
    if (pass.length < 6) {
      setState(() => _error = 'Password must be at least 6 characters.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await FirebaseAuthService.instance
          .linkOrSignInWithEmail(email: email, password: pass);
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on FirebaseAuthException catch (e) {
      if (mounted) {
        setState(() {
          _error = _friendly(e);
          _busy = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Something went wrong. Please try again.';
          _busy = false;
        });
      }
    }
  }

  String _friendly(FirebaseAuthException e) {
    switch (e.code) {
      case 'wrong-password':
      case 'invalid-credential':
        return 'That password does not match. Try again.';
      case 'user-not-found':
        return 'No account found for that email.';
      case 'invalid-email':
        return 'That email address looks invalid.';
      case 'network-request-failed':
        return 'No connection. Check your internet and try again.';
      case 'too-many-requests':
        return 'Too many attempts. Please wait a moment.';
      default:
        return e.message ?? 'Could not sign you in. Please try again.';
    }
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final subtle = isDark
        ? Colors.white.withValues(alpha: 0.60)
        : const Color(0xFF475467);

    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        decoration: BoxDecoration(
          color: cs.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 28),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.20)
                        : Colors.black.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(99),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Text(widget.title,
                  textAlign: TextAlign.center,
                  style: tt.titleLarge?.copyWith(
                      fontWeight: FontWeight.w900,
                      color: isDark ? Colors.white : const Color(0xFF0E1320))),
              const SizedBox(height: 8),
              Text(widget.subtitle,
                  textAlign: TextAlign.center,
                  style: tt.bodyMedium?.copyWith(color: subtle, height: 1.5)),
              const SizedBox(height: 24),

              if (_error != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFF6B6B).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: const Color(0xFFFF6B6B).withValues(alpha: 0.35)),
                  ),
                  child: Text(_error!,
                      style: tt.bodySmall
                          ?.copyWith(color: const Color(0xFFFF6B6B))),
                ),
                const SizedBox(height: 16),
              ],

              // Google
              _SheetButton(
                label: 'Continue with Google',
                icon: Icons.login_rounded,
                background: AppColors.mintDeep,
                onTap: _busy ? null : _google,
                loading: _busy && !_showEmail,
              ),
              const SizedBox(height: 12),

              if (!_showEmail)
                TextButton(
                  onPressed:
                      _busy ? null : () => setState(() => _showEmail = true),
                  child: Text('Continue with email instead',
                      style: tt.bodyMedium?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w700)),
                )
              else ...[
                const SizedBox(height: 8),
                TextField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  autocorrect: false,
                  enabled: !_busy,
                  decoration: const InputDecoration(
                    labelText: 'Email',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _passCtrl,
                  obscureText: true,
                  enabled: !_busy,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 16),
                _SheetButton(
                  label: 'Continue',
                  icon: Icons.arrow_forward_rounded,
                  background: AppColors.primary,
                  onTap: _busy ? null : _email,
                  loading: _busy && _showEmail,
                ),
              ],

              const SizedBox(height: 16),
              Text(
                'By continuing you agree to our Terms and Privacy Policy.',
                textAlign: TextAlign.center,
                style: tt.bodySmall?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.30)
                        : Colors.black.withValues(alpha: 0.30)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SheetButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color background;
  final VoidCallback? onTap;
  final bool loading;
  const _SheetButton({
    required this.label,
    required this.icon,
    required this.background,
    required this.onTap,
    this.loading = false,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: FilledButton.icon(
        onPressed: onTap,
        style: FilledButton.styleFrom(
          backgroundColor: background,
          disabledBackgroundColor: background.withValues(alpha: 0.4),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        icon: loading
            ? const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white),
              )
            : Icon(icon, color: Colors.white, size: 20),
        label: Text(label,
            style: const TextStyle(
                color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
      ),
    );
  }
}
