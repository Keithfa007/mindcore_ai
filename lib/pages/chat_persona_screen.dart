// lib/pages/chat_persona_screen.dart
import 'package:flutter/material.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';

import 'helpers/chat_persona_prefs.dart';

class ChatPersonaScreen extends StatefulWidget {
  const ChatPersonaScreen({super.key});

  @override
  State<ChatPersonaScreen> createState() => _ChatPersonaScreenState();
}

class _ChatPersonaScreenState extends State<ChatPersonaScreen> {
  final _ctrl = TextEditingController();
  bool _loading = true;
  String _preset = ChatPersonaPrefs.defaultProfile().presetName;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final p = await ChatPersonaPrefs.loadPersona();
    if (!mounted) return;
    setState(() {
      _preset = p.presetName;
      _ctrl.text = p.profileText;
      _loading = false;
    });
  }

  Future<void> _save() async {
    final txt = _ctrl.text.trim();
    await ChatPersonaPrefs.savePersona(
      PersonaProfile(presetName: _preset, profileText: txt),
    );
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Persona saved')),
    );
  }

  Future<void> _applyPreset(String presetName) async {
    await ChatPersonaPrefs.setPreset(presetName);
    final p = await ChatPersonaPrefs.loadPersona();
    if (!mounted) return;
    setState(() {
      _preset = p.presetName;
      _ctrl.text = p.profileText;
    });
  }

  Future<void> _reset() async {
    await ChatPersonaPrefs.resetDefault();
    await _load();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Reset to default')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;

    return PageScaffold(
      title: 'Chat Persona',
      body: AnimatedBackdrop(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          child: GlassCard(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(14, 14, 14, 18),
              children: [
                Text(
                  'Choose a preset, then tweak the rules below.',
                  style: t.bodyMedium?.copyWith(
                    color: scheme.onSurface.withValues(alpha: 0.75),
                  ),
                ),
                const SizedBox(height: 12),

                DropdownButtonFormField<String>(
                  initialValue: _preset,
                  decoration: const InputDecoration(
                    labelText: 'Persona preset',
                  ),
                  items: ChatPersonaPrefs.presets.keys
                      .map((k) => DropdownMenuItem(value: k, child: Text(k)))
                      .toList(),
                  onChanged: (v) async {
                    if (v == null) return;
                    await _applyPreset(v);
                  },
                ),

                const SizedBox(height: 12),

                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: scheme.surface,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: scheme.outlineVariant.withValues(alpha: 0.35)),
                  ),
                  child: TextField(
                    controller: _ctrl,
                    minLines: 10,
                    maxLines: 18,
                    decoration: const InputDecoration(
                      border: InputBorder.none,
                      hintText: 'Write persona rules here…',
                    ),
                  ),
                ),

                const SizedBox(height: 12),

                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonal(
                        onPressed: _reset,
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Reset'),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        onPressed: _save,
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12),
                          child: Text('Save'),
                        ),
                      ),
                    ),
                  ],
                ),

                const SizedBox(height: 10),

                Text(
                  'Tip: Keep it short and rule-based. The system prompt already enforces: validation → reframe → micro-step → one question.',
                  style: t.bodySmall?.copyWith(
                    color: scheme.onSurface.withValues(alpha: 0.68),
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
