// lib/pages/chat_persona_screen.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'helpers/chat_persona_prefs.dart';

class ChatPersonaScreen extends StatefulWidget {
  const ChatPersonaScreen({super.key});

  @override
  State<ChatPersonaScreen> createState() => _ChatPersonaScreenState();
}

class _ChatPersonaScreenState extends State<ChatPersonaScreen> {
  bool _loading = true;
  String _preset = ChatPersonaPrefs.defaultProfile().presetName;

  // Maps preset name to a short user-friendly description
  static const _descriptions = <String, _PresetMeta>{
    'Coach+Therapist (Default)': _PresetMeta(
      icon: Icons.self_improvement_rounded,
      subtitle: 'Balanced warmth and practical guidance',
      bullets: [
        'Warm, validating and solution-focused',
        'Gentle reframes with reflective listening',
        'Gives 1\u20132 actionable micro-steps',
        'Ends with one supportive question',
      ],
    ),
    'Therapist (Gentle + Deep)': _PresetMeta(
      icon: Icons.favorite_border_rounded,
      subtitle: 'Slow, empathetic and emotionally grounded',
      bullets: [
        'Leads with empathy and validation',
        'Emotional naming and gentle reframes',
        'Encourages self-compassion and boundaries',
        'Calm and unhurried tone',
      ],
    ),
    'Coach (Action + Momentum)': _PresetMeta(
      icon: Icons.bolt_rounded,
      subtitle: 'Practical, upbeat and action-oriented',
      bullets: [
        'Converts overwhelm into a short plan',
        'Simple bullet steps and next best action',
        'Encourages accountability without guilt',
        'Energetic and forward-moving tone',
      ],
    ),
    'Motivator (Positive + Encouraging)': _PresetMeta(
      icon: Icons.star_rounded,
      subtitle: 'High-energy, hopeful and strengths-focused',
      bullets: [
        'Focuses on strengths, wins and possibilities',
        'Confident encouragement with quick steps',
        'Avoids heavy language — keeps it energising',
        'Best for motivation and mindset shifts',
      ],
    ),
    'Minimalist (Short + Clear)': _PresetMeta(
      icon: Icons.tune_rounded,
      subtitle: 'Ultra-concise responses, no fluff',
      bullets: [
        '1 validation + 1 reframe line only',
        '1 micro-step + 1 question per reply',
        'No extra words or long explanations',
        'Best for users who prefer brevity',
      ],
    ),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final p = await ChatPersonaPrefs.loadPersona();
    if (!mounted) return;
    setState(() {
      _preset  = p.presetName;
      _loading = false;
    });
  }

  Future<void> _selectPreset(String name) async {
    setState(() => _preset = name);
    await ChatPersonaPrefs.setPreset(name);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Persona set to $name'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Chat Persona'),
      body: AnimatedBackdrop(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                children: [
                  // Intro
                  Text(
                    'Choose how MindCore AI speaks and supports you.',
                    style: tt.bodyMedium?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.60)
                          : const Color(0xFF475467),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Preset cards
                  ...ChatPersonaPrefs.presets.keys.map((name) {
                    final meta    = _descriptions[name];
                    final selected = name == _preset;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _PresetCard(
                        name:     name,
                        meta:     meta,
                        selected: selected,
                        isDark:   isDark,
                        tt:       tt,
                        onTap:    () => _selectPreset(name),
                      ),
                    );
                  }),

                  const SizedBox(height: 8),
                  Text(
                    'Your selection is saved automatically and takes effect immediately in chat.',
                    textAlign: TextAlign.center,
                    style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.35)
                          : Colors.black.withValues(alpha: 0.35),
                      height: 1.5,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

// ── Preset metadata ───────────────────────────────────────────────────────────

class _PresetMeta {
  final IconData icon;
  final String subtitle;
  final List<String> bullets;
  const _PresetMeta({
    required this.icon,
    required this.subtitle,
    required this.bullets,
  });
}

// ── Preset card ───────────────────────────────────────────────────────────────

class _PresetCard extends StatelessWidget {
  final String name;
  final _PresetMeta? meta;
  final bool selected;
  final bool isDark;
  final TextTheme tt;
  final VoidCallback onTap;

  const _PresetCard({
    required this.name,
    required this.meta,
    required this.selected,
    required this.isDark,
    required this.tt,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final accent = AppColors.primary;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          color: selected
              ? accent.withValues(alpha: isDark ? 0.12 : 0.07)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.04)
                  : Colors.white),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected
                ? accent.withValues(alpha: 0.60)
                : (isDark
                    ? Colors.white.withValues(alpha: 0.10)
                    : Colors.black.withValues(alpha: 0.08)),
            width: selected ? 1.5 : 0.5,
          ),
        ),
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Icon
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: selected
                    ? accent.withValues(alpha: 0.15)
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.08)
                        : Colors.black.withValues(alpha: 0.05)),
              ),
              child: Icon(
                meta?.icon ?? Icons.psychology_alt_rounded,
                size: 20,
                color: selected
                    ? accent
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.50)
                        : Colors.black.withValues(alpha: 0.40)),
              ),
            ),
            const SizedBox(width: 14),
            // Text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          name,
                          style: tt.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                            color: selected
                                ? accent
                                : (isDark
                                    ? Colors.white
                                    : const Color(0xFF0E1320)),
                          ),
                        ),
                      ),
                      if (selected)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: accent.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                                color: accent.withValues(alpha: 0.35)),
                          ),
                          child: Text(
                            'ACTIVE',
                            style: tt.labelSmall?.copyWith(
                              color: accent,
                              fontWeight: FontWeight.w800,
                              fontSize: 10,
                            ),
                          ),
                        ),
                    ],
                  ),
                  if (meta != null) ...[
                    const SizedBox(height: 3),
                    Text(
                      meta!.subtitle,
                      style: tt.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.50)
                            : const Color(0xFF475467),
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...meta!.bullets.map((b) => Padding(
                          padding: const EdgeInsets.only(bottom: 4),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Padding(
                                padding: const EdgeInsets.only(top: 3),
                                child: Container(
                                  width: 4,
                                  height: 4,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: selected
                                        ? accent.withValues(alpha: 0.70)
                                        : (isDark
                                            ? Colors.white
                                                .withValues(alpha: 0.35)
                                            : Colors.black
                                                .withValues(alpha: 0.30)),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  b,
                                  style: tt.bodySmall?.copyWith(
                                    fontSize: 12,
                                    color: isDark
                                        ? Colors.white.withValues(alpha: 0.55)
                                        : const Color(0xFF64748B),
                                    height: 1.4,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
