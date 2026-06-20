// lib/pages/truth_deck_screen.dart
//
// The Truth Deck — one raw, honest card per day.
// Tap to flip, then "Sit with this" or "Talk about this".

import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/truth_deck_service.dart';
import 'package:mindcore_ai/pages/chat_screen.dart';
import 'package:mindcore_ai/pages/helpers/navigation_helpers.dart';

class TruthDeckScreen extends StatefulWidget {
  const TruthDeckScreen({super.key});
  @override
  State<TruthDeckScreen> createState() => _TruthDeckScreenState();
}

class _TruthDeckScreenState extends State<TruthDeckScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _flipCtrl;
  late final Animation<double> _flipAnimation;

  String _cardText = '';
  bool _flipped = false;
  bool _loading = true;
  bool _actioned = false;

  @override
  void initState() {
    super.initState();
    _flipCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _flipAnimation = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _flipCtrl, curve: Curves.easeInOutBack),
    );
    _loadCard();
  }

  Future<void> _loadCard() async {
    final text = await TruthDeckService.todayCard();
    if (!mounted) return;
    setState(() {
      _cardText = text;
      _loading = false;
    });
  }

  void _flip() {
    if (_flipped || _loading) return;
    HapticFeedback.mediumImpact();
    _flipCtrl.forward();
    setState(() => _flipped = true);
  }

  Future<void> _sitWithThis() async {
    HapticFeedback.selectionClick();
    await TruthDeckService.recordSeen();
    setState(() => _actioned = true);
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  Future<void> _talkAboutThis() async {
    HapticFeedback.selectionClick();
    await TruthDeckService.recordTalked();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      createSlideRoute(ChatScreen(initialMessage: 'I just read this: "$_cardText" — I want to talk about it.')),
    );
  }

  @override
  void dispose() {
    _flipCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Truth Deck'),
      body: AnimatedBackdrop(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Column(
            children: [
              const Spacer(flex: 2),

              // ── Card ────────────────────────────────────────
              if (_loading)
                const SizedBox(
                  height: 300,
                  child: Center(child: CircularProgressIndicator()),
                )
              else
                GestureDetector(
                  onTap: _flip,
                  child: AnimatedBuilder(
                    animation: _flipAnimation,
                    builder: (context, child) {
                      final angle = _flipAnimation.value * pi;
                      final isFront = angle < pi / 2;
                      return Transform(
                        alignment: Alignment.center,
                        transform: Matrix4.identity()
                          ..setEntry(3, 2, 0.001)
                          ..rotateY(angle),
                        child: isFront
                            ? _buildFront(tt, isDark)
                            : Transform(
                                alignment: Alignment.center,
                                transform: Matrix4.identity()..rotateY(pi),
                                child: _buildBack(tt, isDark),
                              ),
                      );
                    },
                  ),
                ),

              const Spacer(),

              // ── Actions (appear after flip) ─────────────────
              AnimatedOpacity(
                opacity: _flipped && !_actioned ? 1.0 : 0.0,
                duration: const Duration(milliseconds: 400),
                child: _flipped && !_actioned
                    ? Column(
                        children: [
                          SizedBox(
                            width: double.infinity,
                            child: FilledButton(
                              onPressed: _talkAboutThis,
                              style: FilledButton.styleFrom(
                                backgroundColor: AppColors.primary,
                                minimumSize: const Size.fromHeight(52),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                              child: Text(
                                'Talk about this',
                                style: tt.titleMedium?.copyWith(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: OutlinedButton(
                              onPressed: _sitWithThis,
                              style: OutlinedButton.styleFrom(
                                minimumSize: const Size.fromHeight(52),
                                side: BorderSide(
                                  color: isDark
                                      ? Colors.white.withValues(alpha: 0.15)
                                      : Colors.black.withValues(alpha: 0.12),
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(14),
                                ),
                              ),
                              child: Text(
                                'Sit with this',
                                style: tt.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w700,
                                  color: isDark
                                      ? Colors.white.withValues(alpha: 0.55)
                                      : const Color(0xFF64748B),
                                ),
                              ),
                            ),
                          ),
                        ],
                      )
                    : const SizedBox.shrink(),
              ),

              // ── Actioned confirmation ───────────────────────
              if (_actioned)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle_rounded,
                          color: AppColors.mintDeep, size: 20),
                      const SizedBox(width: 8),
                      Text(
                        'See you tomorrow.',
                        style: tt.bodyMedium?.copyWith(
                          color: AppColors.mintDeep,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),

              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }

  // ── Front of card (before flip) ─────────────────────────────────
  Widget _buildFront(TextTheme tt, bool isDark) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(minHeight: 300),
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  const Color(0xFF1A2B4A),
                  const Color(0xFF0E1826),
                ]
              : [
                  const Color(0xFFE8F0FF),
                  const Color(0xFFF0F4FF),
                ],
        ),
        border: Border.all(
          color: AppColors.primary.withValues(alpha: 0.25),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: isDark ? 0.15 : 0.08),
            blurRadius: 30,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.auto_awesome_rounded,
            color: AppColors.primary.withValues(alpha: 0.50),
            size: 40,
          ),
          const SizedBox(height: 24),
          Text(
            'Today\u2019s Truth',
            style: tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              letterSpacing: -0.6,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Tap to reveal',
            style: tt.bodyMedium?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.40)
                  : Colors.black.withValues(alpha: 0.35),
            ),
          ),
        ],
      ),
    );
  }

  // ── Back of card (after flip) ───────────────────────────────────
  Widget _buildBack(TextTheme tt, bool isDark) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(minHeight: 300),
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: isDark
              ? [
                  const Color(0xFF162030),
                  const Color(0xFF0C1622),
                ]
              : [
                  const Color(0xFFF8FBFF),
                  const Color(0xFFEDF2FF),
                ],
        ),
        border: Border.all(
          color: AppColors.primary.withValues(alpha: 0.30),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: isDark ? 0.20 : 0.10),
            blurRadius: 30,
            offset: const Offset(0, 12),
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.format_quote_rounded,
            color: AppColors.primary.withValues(alpha: 0.30),
            size: 36,
          ),
          const SizedBox(height: 20),
          Text(
            _cardText,
            textAlign: TextAlign.center,
            style: tt.titleLarge?.copyWith(
              fontWeight: FontWeight.w800,
              height: 1.4,
              letterSpacing: -0.3,
              color: isDark ? Colors.white : const Color(0xFF0E1320),
            ),
          ),
        ],
      ),
    );
  }
}
