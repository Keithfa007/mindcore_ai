// lib/pages/login_screen.dart
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';

import 'email_auth_screen.dart';
import '../services/firebase_auth_service.dart';
import '../services/mood_log_service.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/animated_logo.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  bool _initDone = false;
  bool _busy = false;
  String? _error;

  // Entrance animation
  late final AnimationController _entranceCtrl;
  late final Animation<double> _logoFade;
  late final Animation<Offset> _logoSlide;
  late final Animation<double> _cardFade;
  late final Animation<Offset> _cardSlide;

  @override
  void initState() {
    super.initState();

    _entranceCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );

    _logoFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entranceCtrl,
        curve: const Interval(0.0, 0.60, curve: Curves.easeOut),
      ),
    );
    _logoSlide = Tween<Offset>(
      begin: const Offset(0, 0.08),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entranceCtrl,
        curve: const Interval(0.0, 0.60, curve: Curves.easeOut),
      ),
    );
    _cardFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entranceCtrl,
        curve: const Interval(0.35, 1.0, curve: Curves.easeOut),
      ),
    );
    _cardSlide = Tween<Offset>(
      begin: const Offset(0, 0.06),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _entranceCtrl,
        curve: const Interval(0.35, 1.0, curve: Curves.easeOut),
      ),
    );

    _ensureFirebase();
    _entranceCtrl.forward();
  }

  @override
  void dispose() {
    _entranceCtrl.dispose();
    super.dispose();
  }

  Future<void> _ensureFirebase() async {
    try {
      await Firebase.initializeApp();
      if (mounted) setState(() => _initDone = true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Firebase init failed: $e';
          _initDone = true;
        });
      }
    }
  }

  Future<void> _googleSignIn() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await FirebaseAuthService.instance.signInWithGoogle();
      await MoodLogService.syncFromFirestore();
      await JournalService.syncFromFirestore();
      if (!mounted) return;
      Navigator.of(context).pushReplacementNamed('/home');
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 24),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(height: 20),

                    // ── Animated logo + title ────────────────────────────
                    FadeTransition(
                      opacity: _logoFade,
                      child: SlideTransition(
                        position: _logoSlide,
                        child: Column(
                          children: [
                            // Animated branded logo
                            const AnimatedLogo(size: 150),
                            const SizedBox(height: 24),
                            Text(
                              'MindCore AI',
                              textAlign: TextAlign.center,
                              style: tt.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w900,
                                letterSpacing: -0.8,
                                color: isDark
                                    ? Colors.white
                                    : const Color(0xFF0E1320),
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Your calm, private wellness companion.',
                              textAlign: TextAlign.center,
                              style: tt.bodyMedium?.copyWith(
                                color: isDark
                                    ? Colors.white.withValues(alpha: 0.55)
                                    : const Color(0xFF475467),
                                height: 1.5,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: 36),

                    // ── Sign-in card ─────────────────────────────────────
                    FadeTransition(
                      opacity: _cardFade,
                      child: SlideTransition(
                        position: _cardSlide,
                        child: GlassCard(
                          glowColor: AppColors.glowBlue,
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text(
                                'Sign in to continue',
                                textAlign: TextAlign.center,
                                style: tt.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                  color: isDark
                                      ? Colors.white
                                      : const Color(0xFF0E1320),
                                ),
                              ),
                              const SizedBox(height: 20),

                              if (!_initDone) ...[
                                const Center(child: CircularProgressIndicator()),
                              ] else ...[

                                // Error banner
                                if (_error != null) ...[
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFFF6B6B)
                                          .withValues(alpha: 0.12),
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(
                                        color: const Color(0xFFFF6B6B)
                                            .withValues(alpha: 0.35),
                                      ),
                                    ),
                                    child: Text(
                                      _error!,
                                      style: tt.bodySmall?.copyWith(
                                        color: const Color(0xFFFF6B6B),
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // Email button
                                _AuthButton(
                                  label: 'Continue with Email',
                                  icon: Icons.mail_outline_rounded,
                                  gradient: const LinearGradient(
                                    colors: [
                                      Color(0xFF4D7CFF),
                                      Color(0xFF74C3FF),
                                    ],
                                  ),
                                  glowColor: AppColors.primary,
                                  onTap: () => Navigator.of(context).push(
                                    MaterialPageRoute(
                                        builder: (_) =>
                                            const EmailAuthScreen()),
                                  ),
                                ),
                                const SizedBox(height: 12),

                                // Google button
                                _AuthButton(
                                  label: _busy
                                      ? 'Signing in\u2026'
                                      : 'Continue with Google',
                                  icon: Icons.login_rounded,
                                  gradient: const LinearGradient(
                                    colors: [
                                      Color(0xFF32D0BE),
                                      Color(0xFF89E0CF),
                                    ],
                                  ),
                                  glowColor: AppColors.mintDeep,
                                  onTap: _busy ? null : _googleSignIn,
                                  loading: _busy,
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Footer
                    FadeTransition(
                      opacity: _cardFade,
                      child: Text(
                        'By signing in you agree to our Terms & Privacy Policy.',
                        textAlign: TextAlign.center,
                        style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.25)
                              : Colors.black.withValues(alpha: 0.25),
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ── Gradient auth button ──────────────────────────────────────────────────

class _AuthButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final LinearGradient gradient;
  final Color glowColor;
  final VoidCallback? onTap;
  final bool loading;

  const _AuthButton({
    required this.label,
    required this.icon,
    required this.gradient,
    required this.glowColor,
    this.onTap,
    this.loading = false,
  });

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedOpacity(
        duration: const Duration(milliseconds: 150),
        opacity: onTap == null ? 0.55 : 1.0,
        child: Container(
          height: 54,
          decoration: BoxDecoration(
            gradient: gradient,
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: glowColor.withValues(alpha: 0.30),
                blurRadius: 18,
                offset: const Offset(0, 6),
              ),
            ],
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (loading)
                const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              else
                Icon(icon, color: Colors.white, size: 20),
              const SizedBox(width: 10),
              Text(
                label,
                style: tt.titleSmall?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
