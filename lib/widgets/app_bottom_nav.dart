import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/pages/helpers/navigation_helpers.dart';

import 'package:mindcore_ai/pages/home_screen.dart';
import 'package:mindcore_ai/pages/chat_screen.dart';
import 'package:mindcore_ai/pages/daily_hub_screen.dart';
import 'package:mindcore_ai/pages/learning_screen.dart';
import 'package:mindcore_ai/pages/frequently_asked_screen.dart';
import 'package:mindcore_ai/pages/mood_history_screen.dart';
import 'package:mindcore_ai/pages/profile_screen.dart';
import 'package:mindcore_ai/pages/relax_audio_screen.dart';
import 'package:mindcore_ai/pages/blog_screen.dart';

class AppBottomNav extends StatelessWidget {
  final int currentIndex;
  const AppBottomNav({super.key, required this.currentIndex});

  void _go(BuildContext context, int i) {
    if (i == currentIndex) return;
    switch (i) {
      case 0:
        Navigator.of(context).pushReplacement(createSlideRoute(const HomeScreen()));
        break;
      case 1:
        Navigator.of(context).pushReplacement(createSlideRoute(const ChatScreen()));
        break;
      case 2:
        Navigator.of(context).pushReplacement(createSlideRoute(const DailyHubScreen()));
        break;
      case 3:
        Navigator.of(context).pushReplacement(createSlideRoute(const LearningScreen()));
        break;
      case 4:
        Navigator.of(context).pushReplacement(createSlideRoute(const RelaxAudioScreen()));
        break;
      case 5:
        Navigator.of(context).pushReplacement(createSlideRoute(const MoodHistoryScreen()));
        break;
      case 6:
        Navigator.of(context).pushReplacement(createSlideRoute(const ProfileScreen()));
        break;
      case 7:
        Navigator.of(context).pushReplacement(createSlideRoute(const FrequentlyAskedScreen()));
        break;
      case 8:
        Navigator.of(context).push(createSlideRoute(const BlogScreen()));
        break;
      default:
        Navigator.of(context).pushReplacement(createSlideRoute(const HomeScreen()));
        break;
    }
  }

  Future<void> _openBurgerMenu(BuildContext context) async {
    final theme = Theme.of(context);
    await showModalBottomSheet<int>(
      context: context,
      showDragHandle: true,
      backgroundColor: theme.colorScheme.surface,
      builder: (ctx) => SafeArea(
        child: ListView(
          children: [
            const SizedBox(height: 2),
            _sheetItem(ctx, icon: Icons.home_rounded,         label: 'Home',            index: 0),
            _sheetItem(ctx, icon: Icons.chat_bubble,          label: 'Chat',            index: 1),
            _sheetItem(ctx, icon: Icons.dashboard_rounded,    label: 'Journal',         index: 2),
            _sheetItem(ctx, icon: Icons.self_improvement,     label: 'Learning',        index: 3),
            _sheetItem(ctx, icon: Icons.library_music_rounded,label: 'Relaxing Audio',  index: 4),
            _sheetItem(ctx, icon: Icons.timeline,             label: 'Mood History',    index: 5),
            _sheetItem(ctx, icon: Icons.person,               label: 'Profile',         index: 6),
            _sheetItem(ctx, icon: Icons.help_outline,         label: 'Frequently Asked',index: 7),
            _sheetItem(ctx, icon: Icons.article_rounded,      label: 'Blog',            index: 8),
            const SizedBox(height: 12),
          ],
        ),
      ),
    ).then((selected) {
      if (selected != null) _go(context, selected);
    });
  }

  ListTile _sheetItem(BuildContext ctx,
      {required IconData icon, required String label, required int index}) {
    return ListTile(
      leading: Icon(icon),
      title: Text(label),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => Navigator.pop(ctx, index),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final base = isDark
        ? const Color(0xD9121B2A)
        : Colors.white.withValues(alpha: 0.70);
    final onBar = isDark ? Colors.white : Colors.black87;

    Color colorFor(bool selected) =>
        selected ? onBar : onBar.withValues(alpha: 0.62);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 10),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
          child: Container(
            decoration: BoxDecoration(
              color: base,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: Colors.white.withValues(alpha: isDark ? 0.08 : 0.42),
              ),
              boxShadow: [
                BoxShadow(
                  color: isDark
                      ? Colors.black.withValues(alpha: 0.28)
                      : const Color(0x144D7CFF),
                  blurRadius: 24,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: SizedBox(
                height: 74,
                child: Row(
                  children: [
                    Expanded(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _NavItem(
                            icon: currentIndex == 0
                                ? Icons.home_rounded
                                : Icons.home_outlined,
                            label: 'Home',
                            color: colorFor(currentIndex == 0),
                            selected: currentIndex == 0,
                            onTap: () => _go(context, 0),
                          ),
                          _NavItem(
                            icon: currentIndex == 1
                                ? Icons.chat_bubble
                                : Icons.chat_bubble_outline,
                            label: 'Chat',
                            color: colorFor(currentIndex == 1),
                            selected: currentIndex == 1,
                            onTap: () => _go(context, 1),
                          ),
                        ],
                      ),
                    ),
                    _BurgerButton(
                      onPressed: () =>
                          Navigator.of(context).pushNamed('/reset'),
                      onLongPress: () => _openBurgerMenu(context),
                      fg: onBar,
                    ),
                    Expanded(
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _NavItem(
                            icon: currentIndex == 5
                                ? Icons.timeline
                                : Icons.timeline_outlined,
                            label: 'History',
                            color: colorFor(currentIndex == 5),
                            selected: currentIndex == 5,
                            onTap: () => _go(context, 5),
                          ),
                          _NavItem(
                            icon: currentIndex == 6
                                ? Icons.person
                                : Icons.person_outline,
                            label: 'Profile',
                            color: colorFor(currentIndex == 6),
                            selected: currentIndex == 6,
                            onTap: () => _go(context, 6),
                          ),
                        ],
                      ),
                    ),
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

class _NavItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final textStyle = Theme.of(context).textTheme.labelSmall?.copyWith(
          fontWeight: FontWeight.w700,
          color: color,
        );
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        padding:
            const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected
              ? color.withValues(alpha: 0.08)
              : Colors.transparent,
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: color),
            const SizedBox(height: 2),
            Text(label, style: textStyle),
          ],
        ),
      ),
    );
  }
}

class _BurgerButton extends StatelessWidget {
  final VoidCallback onPressed;
  final VoidCallback? onLongPress;
  final Color fg;
  const _BurgerButton(
      {required this.onPressed, this.onLongPress, required this.fg});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 6),
      child: SizedBox(
        width: 68,
        height: 68,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: 68,
              height: 68,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  colors: [
                    Theme.of(context)
                        .colorScheme
                        .primary
                        .withValues(alpha: 0.18),
                    Colors.transparent,
                  ],
                ),
                shape: BoxShape.circle,
              ),
            ),
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: AppGradients.primaryButton,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: Theme.of(context)
                        .colorScheme
                        .primary
                        .withValues(alpha: 0.28),
                    blurRadius: 22,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: Material(
                color: Colors.transparent,
                shape: const CircleBorder(),
                child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: onPressed,
                  onLongPress: onLongPress,
                  child: const SizedBox(
                    width: 58,
                    height: 58,
                    child:
                        Icon(Icons.spa_outlined, color: Colors.white),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
