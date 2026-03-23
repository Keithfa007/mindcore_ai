// lib/pages/onboarding_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../widgets/page_scaffold.dart';
import '../widgets/glass_card.dart';

class OnboardingScreen extends StatefulWidget {
  final VoidCallback onFinish;
  const OnboardingScreen({super.key, required this.onFinish});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _index = 0;

  static const _pages = <_OnboardPageData>[
    _OnboardPageData(
      title: "You don’t need fixing.",
      subtitle: "You’re not broken. You’re human.",
      icon: Icons.favorite_outline,
    ),
    _OnboardPageData(
      title: "You just need a reset sometimes.",
      subtitle: "Small calm moments can change your whole day.",
      icon: Icons.self_improvement,
    ),
    _OnboardPageData(
      title: "Let’s try one now.",
      subtitle: "A 90-second reset. Calm, kind, private.",
      icon: Icons.spa,
    ),
  ];

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _next() async {
    HapticFeedback.selectionClick();

    if (_index >= _pages.length - 1) {
      widget.onFinish();
      return;
    }
    await _controller.nextPage(
      duration: const Duration(milliseconds: 280),
      curve: Curves.easeOutCubic,
    );
  }

  Future<void> _back() async {
    if (_index == 0) return;
    HapticFeedback.selectionClick();
    await _controller.previousPage(
      duration: const Duration(milliseconds: 260),
      curve: Curves.easeOutCubic,
    );
  }

  void _finish() {
    HapticFeedback.lightImpact();
    widget.onFinish();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLast = _index == _pages.length - 1;

    return PageScaffold(
      // no top bar on purpose: calm + focused
      body: SafeArea(
        bottom: true,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
          child: Column(
            children: [
              const SizedBox(height: 6),

              // Brand header
              Text(
                "MindCore AI",
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0.2,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                "A calm reset, whenever you need it.",
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.75),
                  height: 1.25,
                ),
                textAlign: TextAlign.center,
              ),

              const SizedBox(height: 18),

              // Pages
              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  itemCount: _pages.length,
                  onPageChanged: (i) {
                    setState(() => _index = i);
                    HapticFeedback.selectionClick();
                  },
                  itemBuilder: (context, i) {
                    final p = _pages[i];

                    return Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 520),
                        child: TweenAnimationBuilder<double>(
                          tween: Tween(begin: 0, end: 1),
                          duration: const Duration(milliseconds: 360),
                          curve: Curves.easeOutCubic,
                          builder: (context, t, child) {
                            final dy = (1 - t) * 14;
                            return Opacity(
                              opacity: t,
                              child: Transform.translate(
                                offset: Offset(0, dy),
                                child: child,
                              ),
                            );
                          },
                          child: GlassCard(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  p.icon,
                                  size: 56,
                                  color: theme.colorScheme.primary,
                                ),
                                const SizedBox(height: 14),
                                Text(
                                  p.title,
                                  style: theme.textTheme.headlineSmall?.copyWith(
                                    fontWeight: FontWeight.w900,
                                    height: 1.08,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                                const SizedBox(height: 10),
                                Text(
                                  p.subtitle,
                                  style: theme.textTheme.bodyLarge?.copyWith(
                                    color: theme.colorScheme.onSurface.withValues(alpha: 0.82),
                                    height: 1.35,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                                const SizedBox(height: 6),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),

              const SizedBox(height: 10),

              // Dots
              Semantics(
                label: "Onboarding progress",
                value: "Step ${_index + 1} of ${_pages.length}",
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(_pages.length, (i) {
                    final active = i == _index;
                    return AnimatedContainer(
                      duration: const Duration(milliseconds: 220),
                      curve: Curves.easeOutCubic,
                      margin: const EdgeInsets.symmetric(horizontal: 5),
                      height: 8,
                      width: active ? 24 : 8,
                      decoration: BoxDecoration(
                        color: active
                            ? theme.colorScheme.primary
                            : theme.colorScheme.onSurface.withValues(alpha: 0.25),
                        borderRadius: BorderRadius.circular(20),
                      ),
                    );
                  }),
                ),
              ),

              const SizedBox(height: 14),

              // Buttons
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 520),
                child: Row(
                  children: [
                    // Back (only after first page)
                    if (_index > 0) ...[
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _back,
                          child: const Text("Back"),
                        ),
                      ),
                      const SizedBox(width: 12),
                    ],

                    Expanded(
                      child: OutlinedButton(
                        onPressed: _finish,
                        child: Text(isLast ? "Close" : "Skip"),
                      ),
                    ),
                    const SizedBox(width: 12),

                    Expanded(
                      child: FilledButton(
                        onPressed: _next,
                        child: Text(isLast ? "Start Reset" : "Next"),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _OnboardPageData {
  final String title;
  final String subtitle;
  final IconData icon;
  const _OnboardPageData({
    required this.title,
    required this.subtitle,
    required this.icon,
  });
}
