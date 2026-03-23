import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
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
  bool _enabled = true;
  bool _moodAdaptive = true;
  double _speed = 0.90;
  String _voice = 'nova';
  final Map<TtsSurface, bool> _surfaceEnabled = {
    for (final s in TtsSurface.values) s: s.defaultEnabled,
  };

  static const _voiceOptions = <String>['nova', 'alloy'];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    await OpenAiTtsService.instance.init();
    final values = <TtsSurface, bool>{};
    for (final surface in TtsSurface.values) {
      values[surface] = await OpenAiTtsService.instance.getSurfaceEnabled(surface);
    }
    if (!mounted) return;
    setState(() {
      _enabled = OpenAiTtsService.instance.enabled;
      _moodAdaptive = OpenAiTtsService.instance.moodAdaptive;
      _speed = OpenAiTtsService.instance.baseSpeed;
      _voice = OpenAiTtsService.instance.voice;
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
    return PageScaffold(
      title: 'Voice',
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              children: [
                GlassCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SectionHeroCard(
                        title: 'Voice Settings',
                        subtitle: 'Calm app-wide speech with per-surface controls',
                      ),
                      const SizedBox(height: 8),
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
                      SwitchListTile(
                        title: const Text('Mood-adaptive voice'),
                        subtitle: const Text('Slower and more grounding when mood feels anxious or low'),
                        value: _moodAdaptive,
                        onChanged: _enabled
                            ? (v) async {
                                setState(() => _moodAdaptive = v);
                                await OpenAiTtsService.instance.setMoodAdaptive(v);
                              }
                            : null,
                      ),
                      const Padding(
                        padding: EdgeInsets.fromLTRB(16, 8, 16, 0),
                        child: Text('Voice style'),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                        child: DropdownButtonFormField<String>(
                          initialValue: _voiceOptions.contains(_voice) ? _voice : 'nova',
                          decoration: const InputDecoration(
                            labelText: 'Selected voice',
                            helperText: 'Nova is set as the calm female-style default',
                          ),
                          items: _voiceOptions
                              .map((v) => DropdownMenuItem<String>(
                                    value: v,
                                    child: Text(v[0].toUpperCase() + v.substring(1)),
                                  ))
                              .toList(),
                          onChanged: !_enabled
                              ? null
                              : (v) async {
                                  if (v == null) return;
                                  setState(() => _voice = v);
                                  await OpenAiTtsService.instance.setVoice(v);
                                },
                        ),
                      ),
                      const Padding(
                        padding: EdgeInsets.fromLTRB(16, 0, 16, 0),
                        child: Text('Base speed'),
                      ),
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
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
                        padding: const EdgeInsets.symmetric(horizontal: 16),
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
      case TtsSurface.chat:
        return 'Read new AI replies in chat aloud.';
      case TtsSurface.recommendation:
        return 'Read the home recommendation aloud once per day when enabled.';
      case TtsSurface.dailyMotivation:
        return 'Read the daily motivation / affirmation on app open.';
      case TtsSurface.journal:
        return 'Allow journal pages to be read aloud from the journal screen.';
      case TtsSurface.reflection:
        return 'Allow AI reflections to be read aloud.';
      case TtsSurface.breathe:
        return 'Use spoken inhale / hold / exhale cues in breathing sessions.';
    }
  }
}
