// lib/pages/helpers/mood_picker_sheet.dart
//
// Pops with {'emoji': String, 'label': String} on selection.
// Does NOT call MoodLogService itself — callers handle logging.
import 'package:flutter/material.dart';

class _Mood {
  final String emoji;
  final String label;
  const _Mood(this.emoji, this.label);
}

class MoodPickerSheet extends StatelessWidget {
  const MoodPickerSheet({super.key});

  // ── Mood groups ─────────────────────────────────────────────────────
  // Three groups that cover the real emotional range of this app's users.

  static const _goodMoods = [
    _Mood('\ud83d\ude04', 'Amazing'),
    _Mood('\ud83d\ude0a', 'Happy'),
    _Mood('\ud83d\ude0c', 'Peaceful'),
    _Mood('\ud83d\udcaa', 'Motivated'),
    _Mood('\ud83e\udd70', 'Grateful'),
  ];

  static const _middleMoods = [
    _Mood('\ud83d\ude42', 'Okay'),
    _Mood('\ud83d\ude34', 'Tired'),
    _Mood('\ud83e\udd14', 'Unsettled'),
    _Mood('\ud83d\ude36', 'Numb'),
  ];

  static const _hardMoods = [
    _Mood('\ud83d\ude14', 'Sad'),
    _Mood('\ud83d\ude1f', 'Anxious'),
    _Mood('\ud83d\ude29', 'Overwhelmed'),
    _Mood('\ud83d\ude24', 'Frustrated'),
    _Mood('\ud83d\ude22', 'Tearful'),
    _Mood('\ud83d\ude1e', 'Hopeless'),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;

    return Container(
      decoration: BoxDecoration(
        color: cs.surface,
        borderRadius:
            const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 16),
              decoration: BoxDecoration(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.20)
                    : Colors.black.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),

          // Title
          Text(
            'How are you feeling?',
            style: tt.titleMedium
                ?.copyWith(fontWeight: FontWeight.w800),
          ),
          Text(
            'Be honest — this helps your AI companion support you better.',
            style: tt.bodySmall?.copyWith(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : Colors.black.withValues(alpha: 0.40),
            ),
          ),
          const SizedBox(height: 20),

          // Group: Feeling good
          _GroupLabel(
              label: 'Feeling good',
              color: const Color(0xFF0F6E56),
              isDark: isDark),
          const SizedBox(height: 8),
          _MoodRow(moods: _goodMoods, isDark: isDark, tt: tt),
          const SizedBox(height: 16),

          // Group: Somewhere in the middle
          _GroupLabel(
              label: 'Somewhere in the middle',
              color: const Color(0xFF534AB7),
              isDark: isDark),
          const SizedBox(height: 8),
          _MoodRow(moods: _middleMoods, isDark: isDark, tt: tt),
          const SizedBox(height: 16),

          // Group: Having a hard time
          _GroupLabel(
              label: 'Having a hard time',
              color: const Color(0xFFA32D2D),
              isDark: isDark),
          const SizedBox(height: 8),
          _MoodRow(moods: _hardMoods, isDark: isDark, tt: tt),
          const SizedBox(height: 12),

          // Cancel
          Center(
            child: TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(
                'Cancel',
                style: TextStyle(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.40),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Group label ─────────────────────────────────────────────────────────────

class _GroupLabel extends StatelessWidget {
  final String label;
  final Color color;
  final bool isDark;
  const _GroupLabel(
      {required this.label, required this.color, required this.isDark});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
              shape: BoxShape.circle, color: color),
        ),
        const SizedBox(width: 6),
        Text(
          label.toUpperCase(),
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.8,
            color: isDark
                ? Colors.white.withValues(alpha: 0.40)
                : Colors.black.withValues(alpha: 0.38),
          ),
        ),
      ],
    );
  }
}

// ── Mood row ───────────────────────────────────────────────────────────────

class _MoodRow extends StatelessWidget {
  final List<_Mood> moods;
  final bool isDark;
  final TextTheme tt;
  const _MoodRow(
      {required this.moods, required this.isDark, required this.tt});

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: moods.map((m) {
        return InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () =>
              // Return data to caller — DO NOT log here
              Navigator.pop(
                  context, {'emoji': m.emoji, 'label': m.label}),
          child: Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 12, vertical: 9),
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.07)
                  : Colors.black.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.10)
                    : Colors.black.withValues(alpha: 0.08),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(m.emoji,
                    style: const TextStyle(fontSize: 20)),
                const SizedBox(width: 7),
                Text(
                  m.label,
                  style: tt.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}
