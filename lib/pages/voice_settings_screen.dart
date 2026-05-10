import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/persona_service.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

class VoiceSettingsScreen extends StatefulWidget {
  const VoiceSettingsScreen({super.key});

  @override
  State<VoiceSettingsScreen> createState() => _VoiceSettingsScreenState();
}

class _VoiceSettingsScreenState extends State<VoiceSettingsScreen> {
  bool _loading = true;

  // TTS settings
  bool _enabled     = true;
  bool _moodAdaptive = true;
  double _speed     = 0.96;
  final Map<TtsSurface, bool> _surfaceEnabled = {
    for (final s in TtsSurface.values) s: s.defaultEnabled,
  };

  // Companion preferences
  String _companionGender = 'male'; // 'male' | 'female'
  PersonaStyle _personaStyle = PersonaStyle.standard;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await OpenAiTtsService.instance.init();
    await LiveVoicePreferences.instance.load();
    final currentStyle = await PersonaService.getPersonaStyle();
    final values = <TtsSurface, bool>{};
    for (final surface in TtsSurface.values) {
      values[surface] = await OpenAiTtsService.instance.getSurfaceEnabled(surface);
    }
    if (!mounted) return;
    setState(() {
      _enabled          = OpenAiTtsService.instance.enabled;
      _moodAdaptive     = OpenAiTtsService.instance.moodAdaptive;
      _speed            = OpenAiTtsService.instance.baseSpeed;
      _companionGender  = LiveVoicePreferences.instance.companionGender;
      _personaStyle     = currentStyle;
      _surfaceEnabled..clear()..addAll(values);
      _loading = false;
    });
  }

  Future<void> _testVoice() async {
    await OpenAiTtsService.instance.speak(
      'You are safe. Let your shoulders soften, and take one slow, steady breath with me.',
      moodLabel: 'calm',
      surface: TtsSurface.dailyMotivation,
      force: true,
      messageId: 'voice_test',
    );
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      title: 'Voice',
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              children: [

                // ── Companion Personalisation ─────────────────────────────
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Companion Personalisation',
                        subtitle: 'Choose the voice and style that feels right for you',
                      ),
                      const SizedBox(height: 4),

                      // Voice gender
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                        child: Text('Companion Voice', style: tt.labelLarge),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                        child: Row(
                          children: [
                            Expanded(child: _GenderCard(
                              gender: 'male',
                              title: 'Calm Male',
                              subtitle: 'Deep, grounded',
                              icon: Icons.record_voice_over_rounded,
                              selected: _companionGender == 'male',
                              onTap: () async {
                                setState(() => _companionGender = 'male');
                                await LiveVoicePreferences.instance.setCompanionGender('male');
                              },
                              cs: cs, isDark: isDark, tt: tt,
                            )),
                            const SizedBox(width: 10),
                            Expanded(child: _GenderCard(
                              gender: 'female',
                              title: 'Warm Female',
                              subtitle: 'Warm, relaxing',
                              icon: Icons.record_voice_over_rounded,
                              selected: _companionGender == 'female',
                              onTap: () async {
                                setState(() => _companionGender = 'female');
                                await LiveVoicePreferences.instance.setCompanionGender('female');
                              },
                              cs: cs, isDark: isDark, tt: tt,
                            )),
                          ],
                        ),
                      ),

                      const Divider(height: 24, indent: 16, endIndent: 16),

                      // Companion style
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        child: Text('Companion Style', style: tt.labelLarge),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        child: Text(
                          'Feminine style prioritises emotional presence and warmth before solutions.',
                          style: tt.bodySmall?.copyWith(
                            color: cs.onSurface.withValues(alpha: 0.55),
                          ),
                        ),
                      ),
                      RadioListTile<PersonaStyle>(
                        title: const Text('Standard'),
                        subtitle: const Text('Balanced, warm, direct'),
                        value: PersonaStyle.standard,
                        groupValue: _personaStyle,
                        onChanged: (v) async {
                          if (v == null) return;
                          setState(() => _personaStyle = v);
                          await PersonaService.setPersonaStyle(v);
                        },
                      ),
                      RadioListTile<PersonaStyle>(
                        title: const Text('Feminine'),
                        subtitle: const Text('Warmth first, feelings fully acknowledged'),
                        value: PersonaStyle.feminine,
                        groupValue: _personaStyle,
                        onChanged: (v) async {
                          if (v == null) return;
                          setState(() => _personaStyle = v);
                          await PersonaService.setPersonaStyle(v);
                        },
                      ),
                      const SizedBox(height: 8),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // ── Main controls ─────────────────────────────────────────
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Voice Settings',
                        subtitle: 'Powered by Fish Audio — natural, calm speech',
                      ),
                      const SizedBox(height: 8),

                      // Enable toggle
                      SwitchListTile(
                        title: const Text('Enable voice'),
                        subtitle: const Text('Master switch for all speech in the app'),
                        value: _enabled,
                        onChanged: (v) async {
                          setState(() => _enabled = v);
                          await OpenAiTtsService.instance.setEnabled(v);
                          if (!v) await OpenAiTtsService.instance.stop();
                        },
                      ),

                      // Mood-adaptive
                      SwitchListTile(
                        title: const Text('Mood-adaptive pacing'),
                        subtitle: const Text('Slows delivery when mood feels anxious or low'),
                        value: _moodAdaptive,
                        onChanged: _enabled
                            ? (v) async {
                                setState(() => _moodAdaptive = v);
                                await OpenAiTtsService.instance.setMoodAdaptive(v);
                              }
                            : null,
                      ),

                      // Speed
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                        child: Text('Voice speed', style: tt.labelLarge),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        child: Slider(
                          value: _speed,
                          min: 0.72,
                          max: 1.05,
                          divisions: 22,
                          label: _speed.toStringAsFixed(2),
                          onChanged: !_enabled
                              ? null
                              : (v) async {
                                  setState(() => _speed = v);
                                  await OpenAiTtsService.instance.setBaseSpeed(v);
                                },
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        child: Text(
                          'Note: Fish Audio voice pacing is primarily controlled '
                          'by the voice model itself.',
                          style: tt.bodySmall?.copyWith(
                            color: cs.onSurface.withValues(alpha: 0.45),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),

                      // Test button
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                        child: FilledButton.icon(
                          icon: const Icon(Icons.play_circle_fill_rounded),
                          label: const Text('Test voice'),
                          onPressed: _enabled ? _testVoice : null,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // ── Surface controls ──────────────────────────────────────
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Where voice is used',
                        subtitle: 'Turn each voice surface on or off independently',
                      ),
                      const SizedBox(height: 4),
                      for (final surface in TtsSurface.values)
                        SwitchListTile(
                          title: Text(surface.label),
                          subtitle: Text(_subtitleForSurface(surface)),
                          value: _surfaceEnabled[surface] ?? surface.defaultEnabled,
                          onChanged: !_enabled
                              ? null
                              : (v) async {
                                  setState(() => _surfaceEnabled[surface] = v);
                                  await OpenAiTtsService.instance.setSurfaceEnabled(surface, v);
                                },
                        ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  String _subtitleForSurface(TtsSurface surface) {
    switch (surface) {
      case TtsSurface.chat:            return 'Read new AI replies in chat aloud.';
      case TtsSurface.recommendation:  return 'Read the home recommendation aloud once per day.';
      case TtsSurface.dailyMotivation: return 'Read the daily motivation on app open.';
      case TtsSurface.journal:         return 'Allow journal entries to be read aloud.';
      case TtsSurface.reflection:      return 'Allow AI reflections to be read aloud.';
      case TtsSurface.breathe:         return 'Use spoken inhale / hold / exhale cues in breathing sessions.';
    }
  }
}

// ── Voice gender card ─────────────────────────────────────────────────────────

class _GenderCard extends StatelessWidget {
  final String gender;
  final String title;
  final String subtitle;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;
  final ColorScheme cs;
  final bool isDark;
  final TextTheme tt;
  const _GenderCard({
    required this.gender, required this.title, required this.subtitle,
    required this.icon, required this.selected, required this.onTap,
    required this.cs, required this.isDark, required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 12),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(14),
          color: selected
              ? cs.primary.withValues(alpha: 0.10)
              : (isDark
                  ? Colors.white.withValues(alpha: 0.04)
                  : Colors.black.withValues(alpha: 0.03)),
          border: Border.all(
            color: selected
                ? cs.primary
                : (isDark
                    ? Colors.white.withValues(alpha: 0.10)
                    : Colors.black.withValues(alpha: 0.08)),
            width: selected ? 1.8 : 0.8,
          ),
        ),
        child: Column(
          children: [
            Icon(icon,
                color: selected ? cs.primary : cs.onSurface.withValues(alpha: 0.5),
                size: 28),
            const SizedBox(height: 8),
            Text(title,
                textAlign: TextAlign.center,
                style: tt.titleSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: selected ? cs.primary : null)),
            const SizedBox(height: 4),
            Text(subtitle,
                textAlign: TextAlign.center,
                style: tt.bodySmall?.copyWith(
                    color: cs.onSurface.withValues(alpha: 0.50))),
            if (selected) ...[const SizedBox(height: 8), Icon(Icons.check_circle_rounded, color: cs.primary, size: 18)],
          ],
        ),
      ),
    );
  }
}
