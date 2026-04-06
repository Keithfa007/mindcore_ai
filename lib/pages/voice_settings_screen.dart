import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';
import 'package:mindcore_ai/env/env.dart';

class VoiceSettingsScreen extends StatefulWidget {
  const VoiceSettingsScreen({super.key});

  @override
  State<VoiceSettingsScreen> createState() => _VoiceSettingsScreenState();
}

class _VoiceSettingsScreenState extends State<VoiceSettingsScreen> {
  bool _loading = true;
  bool _enabled = true;
  bool _moodAdaptive = true;
  double _speed = 0.96;
  final Map<TtsSurface, bool> _surfaceEnabled = {
    for (final s in TtsSurface.values) s: s.defaultEnabled,
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await OpenAiTtsService.instance.init();
    final values = <TtsSurface, bool>{};
    for (final surface in TtsSurface.values) {
      values[surface] =
          await OpenAiTtsService.instance.getSurfaceEnabled(surface);
    }
    if (!mounted) return;
    setState(() {
      _enabled      = OpenAiTtsService.instance.enabled;
      _moodAdaptive = OpenAiTtsService.instance.moodAdaptive;
      _speed        = OpenAiTtsService.instance.baseSpeed;
      _surfaceEnabled
        ..clear()
        ..addAll(values);
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

                // ── Main controls ────────────────────────────────────────
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Voice Settings',
                        subtitle: 'Powered by Fish Audio — natural, calm speech',
                      ),
                      const SizedBox(height: 8),

                      // Active voice info pill
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 10),
                          decoration: BoxDecoration(
                            color: cs.primary.withValues(alpha: 0.08),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                                color: cs.primary.withValues(alpha: 0.20)),
                          ),
                          child: Row(
                            children: [
                              Icon(Icons.record_voice_over_rounded,
                                  color: cs.primary, size: 18),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Active voice',
                                      style: tt.labelSmall?.copyWith(
                                        color: cs.onSurface
                                            .withValues(alpha: 0.55),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      'Fish Audio — Custom voice',
                                      style: tt.titleSmall?.copyWith(
                                        fontWeight: FontWeight.w800,
                                        color: isDark
                                            ? Colors.white
                                            : const Color(0xFF0E1320),
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      'ID: ${Env.fishAudioVoiceId}',
                                      style: tt.bodySmall?.copyWith(
                                        color: cs.onSurface
                                            .withValues(alpha: 0.40),
                                        fontSize: 10,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),

                      // Enable toggle
                      SwitchListTile(
                        title: const Text('Enable voice'),
                        subtitle:
                            const Text('Master switch for all speech in the app'),
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
                        subtitle: const Text(
                            'Slows delivery when mood feels anxious or low'),
                        value: _moodAdaptive,
                        onChanged: _enabled
                            ? (v) async {
                                setState(() => _moodAdaptive = v);
                                await OpenAiTtsService.instance
                                    .setMoodAdaptive(v);
                              }
                            : null,
                      ),

                      // Speed note
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 4, 16, 4),
                        child: Text(
                          'Voice speed',
                          style: tt.labelLarge,
                        ),
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
                                  await OpenAiTtsService.instance
                                      .setBaseSpeed(v);
                                },
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 4),
                        child: Text(
                          'Note: Fish Audio voice pacing is primarily controlled '
                          'by the voice model itself. This setting adjusts '
                          'the mood-adaptive offset.',
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

                // ── Surface controls ─────────────────────────────────────
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Where voice is used',
                        subtitle:
                            'Turn each voice surface on or off independently',
                      ),
                      const SizedBox(height: 4),
                      for (final surface in TtsSurface.values)
                        SwitchListTile(
                          title: Text(surface.label),
                          subtitle: Text(_subtitleForSurface(surface)),
                          value: _surfaceEnabled[surface] ??
                              surface.defaultEnabled,
                          onChanged: !_enabled
                              ? null
                              : (v) async {
                                  setState(
                                      () => _surfaceEnabled[surface] = v);
                                  await OpenAiTtsService.instance
                                      .setSurfaceEnabled(surface, v);
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
      case TtsSurface.chat:
        return 'Read new AI replies in chat aloud.';
      case TtsSurface.recommendation:
        return 'Read the home recommendation aloud once per day.';
      case TtsSurface.dailyMotivation:
        return 'Read the daily motivation on app open.';
      case TtsSurface.journal:
        return 'Allow journal entries to be read aloud.';
      case TtsSurface.reflection:
        return 'Allow AI reflections to be read aloud.';
      case TtsSurface.breathe:
        return 'Use spoken inhale / hold / exhale cues in breathing sessions.';
    }
  }
}
