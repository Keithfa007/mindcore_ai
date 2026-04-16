import 'package:flutter/material.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';

import 'package:mindcore_ai/pages/helpers/mood_picker_sheet.dart';
import 'package:mindcore_ai/services/reset_metrics_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';
import 'package:mindcore_ai/widgets/tts_replay_button.dart';

class ResetScreen extends StatefulWidget {
  const ResetScreen({super.key});

  @override
  State<ResetScreen> createState() => _ResetScreenState();
}

class _ResetScreenState extends State<ResetScreen>
    with AutoStopTtsRouteAware<ResetScreen> {
  String _moodLabel = 'Neutral';
  String _moodEmoji = '🙂';

  int _before = 6;
  int _after = 4;

  bool _didBreathing = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
  }

  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      if (mounted) Navigator.of(context).pop();
    }
  }

  Future<void> _pickMood() async {
    final res = await showModalBottomSheet<Map<String, String>?>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (_) => const _SheetShell(child: MoodPickerSheet()),
    );
    if (res == null) return;
    setState(() {
      _moodLabel = res['label'] ?? 'Neutral';
      _moodEmoji = res['emoji'] ?? '🙂';
    });
  }

  Future<void> _startBreathing() async {
    setState(() => _didBreathing = true);
    await Navigator.of(context).pushNamed('/breathe');
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _finish() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      final now = DateTime.now();

      // Save reset metrics (stress before/after)
      await ResetMetricsService.log(
        timestamp: now,
        beforeStress: _before,
        afterStress: _after,
        moodLabel: _moodLabel,
      );

      // Also save to mood log so it appears in History page
      await MoodLogService.logMood(
        emoji: _moodEmoji,
        label: _moodLabel,
        note: 'Logged after Quick Reset (stress: $_before → $_after)',
        timestamp: now,
      );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Reset saved. Nice work.')),
      );
      Navigator.of(context).pop();
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      title: 'Quick Reset',
      bottomIndex: null,
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          GlassCard(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '60 seconds to calmer.',
                    style:
                        TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'No analysis. Just a reset.',
                    style: TextStyle(color: Theme.of(context).hintColor),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('Mood: $_moodEmoji  $_moodLabel'),
                      const Spacer(),
                      TextButton(
                        onPressed: _pickMood,
                        child: const Text('Change'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _sliderCard(
            title: 'Stress before',
            value: _before,
            onChanged: (v) => setState(() => _before = v),
          ),
          const SizedBox(height: 12),
          GlassCard(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Breathing',
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tap start. Come back when you\'re done.',
                    style: TextStyle(color: Theme.of(context).hintColor),
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: _startBreathing,
                      icon: const Icon(Icons.spa_outlined),
                      label: Text(_didBreathing
                          ? 'Do another round'
                          : 'Start breathing'),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          _sliderCard(
            title: 'Stress after',
            value: _after,
            onChanged: (v) => setState(() => _after = v),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: _saving ? null : _finish,
                  child: Text(_saving ? 'Saving…' : 'Finish reset'),
                ),
              ),
              const SizedBox(width: 10),
              const TtsReplayButton(surface: TtsSurface.dailyMotivation),
            ],
          ),
        ],
      ),
    );
  }

  Widget _sliderCard({
    required String title,
    required int value,
    required ValueChanged<int> onChanged,
  }) {
    return GlassCard(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title,
                style: const TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Row(
              children: [
                Text(value.toString(),
                    style: const TextStyle(
                        fontSize: 22, fontWeight: FontWeight.w800)),
                const SizedBox(width: 12),
                Expanded(
                  child: Slider(
                    min: 1,
                    max: 10,
                    divisions: 9,
                    value: value.toDouble(),
                    onChanged: (d) => onChanged(d.round()),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SheetShell extends StatelessWidget {
  final Widget child;
  const _SheetShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(18),
      ),
      child: child,
    );
  }
}
