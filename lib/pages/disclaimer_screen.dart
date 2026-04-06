// lib/pages/disclaimer_screen.dart
//
// Full disclaimer text — linked from Settings and shown during onboarding.

import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class DisclaimerScreen extends StatelessWidget {
  const DisclaimerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs     = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: const Text('Disclaimer'),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: AnimatedBackdrop(
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 32),
            children: [
              // Header icon
              Center(
                child: Container(
                  width: 64,
                  height: 64,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.primary.withValues(alpha: 0.12),
                    border: Border.all(
                        color: AppColors.primary.withValues(alpha: 0.30)),
                  ),
                  child: Icon(Icons.info_outline_rounded,
                      color: AppColors.primary, size: 32),
                ),
              ),
              const SizedBox(height: 20),

              Text(
                'Important — Please Read',
                textAlign: TextAlign.center,
                style: tt.titleLarge?.copyWith(
                  fontWeight: FontWeight.w900,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                ),
              ),
              const SizedBox(height: 24),

              // Main disclaimer card
              GlassCard(
                glowColor: AppColors.glowBlue,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _Section(
                      icon: Icons.smart_toy_rounded,
                      color: AppColors.primary,
                      title: 'Not a medical or mental health service',
                      body:
                          'MindCore AI is a personal wellness companion app. '
                          'It is not a licensed mental health service, therapy platform, '
                          'medical device, or clinical tool of any kind.',
                      tt: tt,
                      isDark: isDark,
                    ),
                    const SizedBox(height: 16),
                    _Section(
                      icon: Icons.person_rounded,
                      color: AppColors.mintDeep,
                      title: 'No substitute for professional help',
                      body:
                          'The AI responses in this app are not a replacement for '
                          'professional psychological advice, diagnosis, or treatment. '
                          'Always seek the guidance of a qualified mental health professional '
                          'with any questions or concerns you may have.',
                      tt: tt,
                      isDark: isDark,
                    ),
                    const SizedBox(height: 16),
                    _Section(
                      icon: Icons.warning_amber_rounded,
                      color: const Color(0xFFFF6B6B),
                      title: 'In a crisis or emergency',
                      body:
                          'If you are experiencing a mental health crisis, '
                          'thoughts of suicide or self-harm, or any other emergency, '
                          'please contact your local emergency services immediately '
                          'or call a crisis helpline in your country.',
                      tt: tt,
                      isDark: isDark,
                    ),
                    const SizedBox(height: 16),
                    _Section(
                      icon: Icons.lock_rounded,
                      color: AppColors.violet,
                      title: 'Your conversations',
                      body:
                          'Conversations are processed securely. '
                          'MindCore AI does not store identifiable conversation content '
                          'on our servers. Your journal entries are saved locally on your device.',
                      tt: tt,
                      isDark: isDark,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Crisis resources
              GlassCard(
                glowColor: const Color(0x44FF6B6B),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.phone_rounded,
                            color: Color(0xFFFF6B6B), size: 18),
                        const SizedBox(width: 8),
                        Text(
                          'Crisis Resources',
                          style: tt.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                            color: const Color(0xFFFF6B6B),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    _CrisisLine(
                        country: 'International',
                        number: 'findahelpline.com',
                        tt: tt,
                        isDark: isDark),
                    _CrisisLine(
                        country: 'Malta',
                        number: '1579 (Mental Health Helpline)',
                        tt: tt,
                        isDark: isDark),
                    _CrisisLine(
                        country: 'USA / Canada',
                        number: '988 (Suicide & Crisis Lifeline)',
                        tt: tt,
                        isDark: isDark),
                    _CrisisLine(
                        country: 'UK & Ireland',
                        number: '116 123 (Samaritans)',
                        tt: tt,
                        isDark: isDark),
                    _CrisisLine(
                        country: 'Australia',
                        number: '13 11 14 (Lifeline)',
                        tt: tt,
                        isDark: isDark),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              Text(
                'By using MindCore AI you acknowledge that you have '
                'read and understood this disclaimer.',
                textAlign: TextAlign.center,
                style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.40)
                      : Colors.black.withValues(alpha: 0.40),
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String body;
  final TextTheme tt;
  final bool isDark;

  const _Section({
    required this.icon,
    required this.color,
    required this.title,
    required this.body,
    required this.tt,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withValues(alpha: 0.12),
          ),
          child: Icon(icon, color: color, size: 18),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: tt.titleSmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  color:
                      isDark ? Colors.white : const Color(0xFF0E1320),
                ),
              ),
              const SizedBox(height: 4),
              Text(
                body,
                style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.62)
                      : const Color(0xFF475467),
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _CrisisLine extends StatelessWidget {
  final String country;
  final String number;
  final TextTheme tt;
  final bool isDark;

  const _CrisisLine({
    required this.country,
    required this.number,
    required this.tt,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$country: ',
            style: tt.bodySmall?.copyWith(
              fontWeight: FontWeight.w800,
              color:
                  isDark ? Colors.white.withValues(alpha: 0.75) : const Color(0xFF0E1320),
            ),
          ),
          Expanded(
            child: Text(
              number,
              style: tt.bodySmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.55)
                    : const Color(0xFF475467),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
