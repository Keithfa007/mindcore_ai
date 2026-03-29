// lib/pages/breathe_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../widgets/page_scaffold.dart';
import '../widgets/surfaces.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/breathing_lungs.dart';

// ✅ Use your OpenAI TTS service
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/ai_breathing_coach_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class BreatheScreen extends StatefulWidget {
  const BreatheScreen({super.key});
  @override
  State<BreatheScreen> createState() => _BreatheScreenState();
}

enum _Phase { inhale, hold1, exhale, hold2 }

enum _Preset { box, equal, fourSevenEight, custom }

class _BreatheSettings {
  final _Preset preset;
  final int inhaleS, hold1S, exhaleS, hold2S; // seconds
  final bool haptics;
  final int targetCycles; // 0 = infinite
  final bool tts; // ✅ voice cues

  const _BreatheSettings({
    required this.preset,
    required this.inhaleS,
    required this.hold1S,
    required this.exhaleS,
    required this.hold2S,
    required this.haptics,
    required this.targetCycles,
    required this.tts,
  });

  _BreatheSettings copyWith({
    _Preset? preset,
    int? inhaleS,
    int? hold1S,
    int? exhaleS,
    int? hold2S,
    bool? haptics,
    int? targetCycles,
    bool? tts,
  }) {
    return _BreatheSettings(
      preset: preset ?? this.preset,
      inhaleS: inhaleS ?? this.inhaleS,
      hold1S: hold1S ?? this.hold1S,
      exhaleS: exhaleS ?? this.exhaleS,
      hold2S: hold2S ?? this.hold2S,
      haptics: haptics ?? this.haptics,
      targetCycles: targetCycles ?? this.targetCycles,
      tts: tts ?? this.tts,
    );
  }
}

class _BreathePrefs {
  static const _kPreset = 'breathe_preset_v1';
  static const _kInhale = 'breathe_inhale_s_v1';
  static const _kHold1 = 'breathe_hold1_s_v1';
  static const _kExhale = 'breathe_exhale_s_v1';
  static const _kHold2 = 'breathe_hold2_s_v1';
  static const _kHapt = 'breathe_haptics_v1';
  static const _kTarget = 'breathe_target_cycles_v1';
  static const _kTts = 'breathe_tts_v1';

  static const _default = _BreatheSettings(
    preset: _Preset.box,
    inhaleS: 4,
    hold1S: 4,
    exhaleS: 4,
    hold2S: 4,
    haptics: true,
    targetCycles: 0,
    tts: false,
  );

  static Future<_BreatheSettings> load() async {
    final p = await SharedPreferences.getInstance();
    final presetStr = p.getString(_kPreset) ?? 'box';
    final preset = <String, _Preset>{
          'box': _Preset.box,
          'equal': _Preset.equal,
          '478': _Preset.fourSevenEight,
          'custom': _Preset.custom,
        }[presetStr] ??
        _Preset.box;

    return _BreatheSettings(
      preset: preset,
      inhaleS: p.getInt(_kInhale) ?? _default.inhaleS,
      hold1S: p.getInt(_kHold1) ?? _default.hold1S,
      exhaleS: p.getInt(_kExhale) ?? _default.exhaleS,
      hold2S: p.getInt(_kHold2) ?? _default.hold2S,
      haptics: p.getBool(_kHapt) ?? _default.haptics,
      targetCycles: p.getInt(_kTarget) ?? _default.targetCycles,
      tts: p.getBool(_kTts) ?? _default.tts,
    );
  }

  static Future<void> save(_BreatheSettings s) async {
    final p = await SharedPreferences.getInstance();
    final presetStr = <_Preset, String>{
      _Preset.box: 'box',
      _Preset.equal: 'equal',
      _Preset.fourSevenEight: '478',
      _Preset.custom: 'custom',
    }[s.preset]!;
    await p.setString(_kPreset, presetStr);
    await p.setInt(_kInhale, s.inhaleS);
    await p.setInt(_kHold1, s.hold1S);
    await p.setInt(_kExhale, s.exhaleS);
    await p.setInt(_kHold2, s.hold2S);
    await p.setBool(_kHapt, s.haptics);
    await p.setInt(_kTarget, s.targetCycles);
    await p.setBool(_kTts, s.tts);
  }
}

class _BreatheScreenState extends State<BreatheScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  late Duration _dInhale, _dHold1, _dExhale, _dHold2;
  Duration get _cycle => _dInhale + _dHold1 + _dExhale + _dHold2;

  _BreatheSettings _settings = _BreathePrefs._default;

  bool _running = false;
  int _completedCycles = 0;

  // ✅ No setState per frame; text listens to notifier
  final ValueNotifier<_Phase> _phaseVN = ValueNotifier<_Phase>(_Phase.inhale);

  // ✅ cycles text listens to notifier (so it updates even without setState)
  final ValueNotifier<int> _cyclesVN = ValueNotifier<int>(0);

  _Phase? _lastSpokenPhase;
  bool _aiCoachEnabled = true;
  bool _loadingCoach = false;
  String _coachMoodLabel = 'calm';
  AiBreathingCoachPlan _coachPlan = AiBreathingCoachPlan.fallback('calm');

  // ✅ used to detect wrap (1.0 -> 0.0) during repeat
  double _lastAnimValue = 0.0;

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
    _applyDurationsFrom(_settings);

    _c = AnimationController(vsync: this, duration: _cycle)
      ..addListener(_onTick);

    _loadSettings();
    _loadCoachPref();
  }

  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      if (mounted) Navigator.of(context).pop();
    }
  }

  Future<void> _loadSettings() async {
    final s = await _BreathePrefs.load();
    if (!mounted) return;
    setState(() {
      _settings = s;
      _applyDurationsFrom(_settings);
      _c.duration = _cycle;
    });
  }

  Future<void> _loadCoachPref() async {
    _aiCoachEnabled = await LiveVoicePreferences.getAiBreathingCoachEnabled();
    if (mounted) setState(() {});
  }

  String get _presetName {
    switch (_settings.preset) {
      case _Preset.box:
        return 'Box';
      case _Preset.equal:
        return 'Equal';
      case _Preset.fourSevenEight:
        return '4-7-8';
      case _Preset.custom:
        return 'Custom';
    }
  }

  Future<void> _prepareAiCoach() async {
    if (!_aiCoachEnabled) return;
    setState(() => _loadingCoach = true);
    final plan = await AiBreathingCoachService.buildPlan(
        moodLabel: _coachMoodLabel, presetName: _presetName);
    if (!mounted) return;
    setState(() {
      _coachPlan = plan;
      _loadingCoach = false;
    });
  }

  void _applyDurationsFrom(_BreatheSettings s) {
    _dInhale = Duration(seconds: s.inhaleS);
    _dHold1 = Duration(seconds: s.hold1S);
    _dExhale = Duration(seconds: s.exhaleS);
    _dHold2 = Duration(seconds: s.hold2S);
  }

  void _stopWithTargetReached() {
    _running = false;
    _c.stop();
    OpenAiTtsService.instance.stop();
    if (_settings.haptics) HapticFeedback.mediumImpact();
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Target reached')),
      );
      setState(() {}); // update Start/Pause label
    }
  }

  void _onTick() {
    // ✅ Detect wrap while repeating: value decreases => new cycle started
    if (_running) {
      if (_c.value < _lastAnimValue) {
        _completedCycles++;
        _cyclesVN.value = _completedCycles;

        if (_settings.targetCycles > 0 &&
            _completedCycles >= _settings.targetCycles) {
          _stopWithTargetReached();
          _lastAnimValue = _c.value;
          return;
        }
      }
    }
    _lastAnimValue = _c.value;

    // ---- Phase logic ----
    final t = _c.value * _cycle.inMilliseconds;
    final a = _dInhale.inMilliseconds;
    final b = _dHold1.inMilliseconds;
    final c = _dExhale.inMilliseconds;

    _Phase next;
    if (t < a) {
      next = _Phase.inhale;
    } else if (t < a + b) {
      next = _Phase.hold1;
    } else if (t < a + b + c) {
      next = _Phase.exhale;
    } else {
      next = _Phase.hold2;
    }

    if (next != _phaseVN.value) {
      _phaseVN.value = next;

      if (_settings.haptics) HapticFeedback.lightImpact();
      _speakPhase(next);
    }
    // ✅ no setState here
  }

  Future<void> _speakPhase(_Phase p) async {
    if (!_settings.tts) return;
    if (!_running) return;

    if (_lastSpokenPhase == p) return;
    _lastSpokenPhase = p;

    String text;
    switch (p) {
      case _Phase.inhale:
        text = _aiCoachEnabled ? _coachPlan.inhale : 'Inhale';
        break;
      case _Phase.exhale:
        text = _aiCoachEnabled ? _coachPlan.exhale : 'Exhale';
        break;
      case _Phase.hold1:
      case _Phase.hold2:
        text = _aiCoachEnabled ? _coachPlan.hold : 'Hold';
        break;
    }

    await OpenAiTtsService.instance.speak(
      text,
      moodLabel: 'calm',
      messageId: 'breathe_phase',
      surface: TtsSurface.breathe,
    );
  }

  @override
  void dispose() {
    _c.dispose();
    _phaseVN.dispose();
    _cyclesVN.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  void _toggle() async {
    if (_running) {
      _c.stop();
      OpenAiTtsService.instance.stop();
      setState(() => _running = false);
      return;
    }

    // ✅ start / resume
    _completedCycles = 0;
    _coachMoodLabel = _settings.tts ? 'calm' : 'neutral';
    await _prepareAiCoach();
    _cyclesVN.value = 0;
    _lastSpokenPhase = null;

    // ensure correct duration
    _c.duration = _cycle;

    // important: baseline for wrap detection
    _lastAnimValue = _c.value;

    // ✅ use repeat for consistent cycling
    _c.repeat(period: _cycle);

    if (_aiCoachEnabled && _settings.tts && _coachPlan.intro.isNotEmpty) {
      await OpenAiTtsService.instance.speak(_coachPlan.intro,
          moodLabel: 'calm',
          messageId: 'breathe_intro',
          surface: TtsSurface.breathe);
    }
    _speakPhase(_phaseVN.value);
    setState(() => _running = true);
  }

  void _reset() {
    _c.stop();
    _c.value = 0;
    _running = false;

    _completedCycles = 0;
    _cyclesVN.value = 0;

    _phaseVN.value = _Phase.inhale;
    _lastSpokenPhase = null;

    _lastAnimValue = 0.0;

    OpenAiTtsService.instance.stop();
    setState(() {});
  }

  Future<void> _openSettings() async {
    final updated = await showModalBottomSheet<_BreatheSettings>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => _BreatheSettingsSheet(initial: _settings),
    );
    if (updated == null) return;

    await _BreathePrefs.save(updated);
    if (!mounted) return;

    setState(() {
      _settings = updated;
      _applyDurationsFrom(_settings);
      _c.duration = _cycle;

      _c.stop();
      _c.value = 0.0;

      _completedCycles = 0;
      _cyclesVN.value = 0;

      _phaseVN.value = _Phase.inhale;
      _lastSpokenPhase = null;
      _lastAnimValue = 0.0;

      if (_running) {
        _c.repeat(period: _cycle);
        _speakPhase(_phaseVN.value);
      } else {
        OpenAiTtsService.instance.stop();
      }
    });
  }

  String _phaseLabel(_Phase p) {
    switch (p) {
      case _Phase.inhale:
        return 'Inhale';
      case _Phase.hold1:
      case _Phase.hold2:
        return 'Hold';
      case _Phase.exhale:
        return 'Exhale';
    }
  }

  String _guidance(_Phase p) {
    if (p == _Phase.inhale) return 'Breathe in gently';
    if (p == _Phase.exhale) return 'Breathe out slowly';
    return 'Hold still';
  }

  double _phaseLocalProgress() {
    final ms = _c.value * _cycle.inMilliseconds;
    final a = _dInhale.inMilliseconds;
    final b = _dHold1.inMilliseconds;
    final c = _dExhale.inMilliseconds;
    final d = _dHold2.inMilliseconds;

    double safeDiv(double num, int den) =>
        den == 0 ? 1.0 : (num / den).clamp(0.0, 1.0);

    if (ms < a) return safeDiv(ms, a);
    if (ms < a + b) return safeDiv(ms - a, b);
    if (ms < a + b + c) return safeDiv(ms - a - b, c);
    return safeDiv(ms - a - b - c, d);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final t = Theme.of(context).textTheme;

    return PageScaffold(
      title: 'Gentle Breathing',
      bottomIndex: 2,
      body: AnimatedBackdrop(
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 18),
            child: Column(
              children: [
                // TOP: title + settings
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Breathe',
                        style:
                            t.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                      ),
                    ),
                    IconButton(
                      tooltip: 'Settings',
                      icon: const Icon(Icons.tune_rounded),
                      onPressed: _openSettings,
                    ),
                  ],
                ),
                const SizedBox(height: 6),

                // ✅ Phase text updates smoothly via ValueNotifier
                ValueListenableBuilder<_Phase>(
                  valueListenable: _phaseVN,
                  builder: (_, phase, __) {
                    return AnimatedSwitcher(
                      duration: const Duration(milliseconds: 220),
                      transitionBuilder: (child, anim) =>
                          FadeTransition(opacity: anim, child: child),
                      child: Column(
                        key: ValueKey(_phaseLabel(phase)),
                        children: [
                          Text(
                            _phaseLabel(phase),
                            style: t.headlineMedium?.copyWith(
                              fontWeight: FontWeight.w900,
                              color: scheme.onSurface,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            _guidance(phase),
                            style: t.bodyMedium?.copyWith(
                              color: scheme.onSurface.withValues(alpha: 0.65),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),

                const SizedBox(height: 10),
                SurfaceCard(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(Icons.record_voice_over_rounded),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _aiCoachEnabled
                                  ? 'AI breathing coach is on'
                                  : 'Classic breathing cues',
                              style: t.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _loadingCoach
                                  ? 'Preparing a real-time guided rhythm…'
                                  : (_aiCoachEnabled
                                      ? _coachPlan.outro
                                      : 'Use simple inhale, hold, and exhale cues.'),
                              style: t.bodySmall?.copyWith(
                                  color:
                                      scheme.onSurface.withValues(alpha: 0.72)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 10),

                // MIDDLE: lungs
                Expanded(
                  child: Center(
                    child: AnimatedBuilder(
                      animation: _c,
                      builder: (_, __) {
                        final p = _phaseLocalProgress();
                        final phase = _phaseVN.value;

                        // Bigger lungs + smooth scale
                        double sx, sy;
                        switch (phase) {
                          case _Phase.inhale:
                            sx = _lerp(0.98, 1.18, Curves.easeOut.transform(p));
                            sy = _lerp(0.98, 1.30, Curves.easeOut.transform(p));
                            break;
                          case _Phase.hold1:
                            sx = 1.18;
                            sy = 1.30;
                            break;
                          case _Phase.exhale:
                            sx = _lerp(
                                1.18, 0.92, Curves.easeInOut.transform(p));
                            sy = _lerp(
                                1.30, 0.88, Curves.easeInOut.transform(p));
                            break;
                          case _Phase.hold2:
                            sx = 0.92;
                            sy = 0.88;
                            break;
                        }

                        return RepaintBoundary(
                          child: Transform.scale(
                            scale: 1.10,
                            child: BreathingLungs(scaleX: sx, scaleY: sy),
                          ),
                        );
                      },
                    ),
                  ),
                ),

                // status line (✅ cycles uses ValueNotifier so it updates)
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.all_inclusive,
                        size: 18,
                        color: scheme.onSurface.withValues(alpha: 0.6)),
                    const SizedBox(width: 6),
                    ValueListenableBuilder<int>(
                      valueListenable: _cyclesVN,
                      builder: (_, cycles, __) {
                        return Text(
                          '$cycles cycle${cycles == 1 ? '' : 's'}',
                          style: t.bodySmall?.copyWith(
                            color: scheme.onSurface.withValues(alpha: 0.65),
                            fontWeight: FontWeight.w700,
                          ),
                        );
                      },
                    ),
                    if (_settings.targetCycles > 0) ...[
                      const SizedBox(width: 12),
                      Text('•',
                          style: t.bodySmall?.copyWith(
                              color: scheme.onSurface.withValues(alpha: 0.55))),
                      const SizedBox(width: 12),
                      Text(
                        'Target ${_settings.targetCycles}',
                        style: t.bodySmall?.copyWith(
                          color: scheme.onSurface.withValues(alpha: 0.65),
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ],
                ),

                const SizedBox(height: 12),

                // BOTTOM: buttons
                Row(
                  children: [
                    Expanded(
                      child: GradientButton.primary(
                        _running ? 'Pause' : 'Start',
                        onPressed: _toggle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: GradientButton.mint(
                        'Reset',
                        onPressed: _reset,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  double _lerp(double a, double b, double t) => a + (b - a) * t;
}

// -------- Settings bottom sheet --------

class _BreatheSettingsSheet extends StatefulWidget {
  final _BreatheSettings initial;
  const _BreatheSettingsSheet({required this.initial});

  @override
  State<_BreatheSettingsSheet> createState() => _BreatheSettingsSheetState();
}

class _BreatheSettingsSheetState extends State<_BreatheSettingsSheet> {
  late _Preset _preset;
  late int _inh, _h1, _exh, _h2;
  late bool _haptics;
  late int _target;
  late bool _tts;

  @override
  void initState() {
    super.initState();
    _preset = widget.initial.preset;
    _inh = widget.initial.inhaleS;
    _h1 = widget.initial.hold1S;
    _exh = widget.initial.exhaleS;
    _h2 = widget.initial.hold2S;
    _haptics = widget.initial.haptics;
    _target = widget.initial.targetCycles;
    _tts = widget.initial.tts;
  }

  void _applyPreset(_Preset p) {
    setState(() {
      _preset = p;
      switch (p) {
        case _Preset.box:
          _inh = 4;
          _h1 = 4;
          _exh = 4;
          _h2 = 4;
          break;
        case _Preset.equal:
          _inh = 5;
          _h1 = 0;
          _exh = 5;
          _h2 = 0;
          break;
        case _Preset.fourSevenEight:
          _inh = 4;
          _h1 = 7;
          _exh = 8;
          _h2 = 0;
          break;
        case _Preset.custom:
          break;
      }
    });
  }

  Widget _chip(String label, _Preset value) {
    final sel = _preset == value;
    return ChoiceChip(
      label: Text(label),
      selected: sel,
      onSelected: (_) => _applyPreset(value),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final viewInsets = MediaQuery.of(context).viewInsets.bottom;
    return Padding(
      padding: EdgeInsets.only(bottom: viewInsets),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 44,
                  height: 5,
                  margin: const EdgeInsets.only(bottom: 14),
                  decoration: BoxDecoration(
                    color: cs.outlineVariant,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
              ),
              Text(
                'Breathing Settings',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(height: 12),

              Text('Technique', style: Theme.of(context).textTheme.labelLarge),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  _chip('Box 4-4-4-4', _Preset.box),
                  _chip('Equal 5-5', _Preset.equal),
                  _chip('4-7-8', _Preset.fourSevenEight),
                  _chip('Custom', _Preset.custom),
                ],
              ),

              if (_preset == _Preset.custom) ...[
                const SizedBox(height: 16),
                _LabeledSlider(
                  label: 'Inhale',
                  value: _inh.toDouble(),
                  min: 1,
                  max: 12,
                  divisions: 11,
                  onChanged: (v) => setState(() => _inh = v.round()),
                ),
                _LabeledSlider(
                  label: 'Hold 1',
                  value: _h1.toDouble(),
                  min: 0,
                  max: 12,
                  divisions: 12,
                  onChanged: (v) => setState(() => _h1 = v.round()),
                ),
                _LabeledSlider(
                  label: 'Exhale',
                  value: _exh.toDouble(),
                  min: 1,
                  max: 16,
                  divisions: 15,
                  onChanged: (v) => setState(() => _exh = v.round()),
                ),
                _LabeledSlider(
                  label: 'Hold 2',
                  value: _h2.toDouble(),
                  min: 0,
                  max: 12,
                  divisions: 12,
                  onChanged: (v) => setState(() => _h2 = v.round()),
                ),
              ] else ...[
                const SizedBox(height: 12),
                _ReadOnlyDurations(inh: _inh, h1: _h1, exh: _exh, h2: _h2),
              ],

              const SizedBox(height: 14),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Haptics (phase change)'),
                value: _haptics,
                onChanged: (v) => setState(() => _haptics = v),
              ),

              // ✅ Voice cues toggle
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Voice cues (OpenAI TTS)'),
                subtitle: const Text('Speaks “Inhale / Hold / Exhale”'),
                value: _tts,
                onChanged: (v) => setState(() => _tts = v),
              ),

              const SizedBox(height: 8),
              _LabeledSlider(
                label: 'Target cycles (0 = infinite)',
                value: _target.toDouble(),
                min: 0,
                max: 12,
                divisions: 12,
                onChanged: (v) => setState(() => _target = v.round()),
              ),

              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Padding(
                        padding: EdgeInsets.symmetric(vertical: 14),
                        child: Text('Cancel'),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: GradientButton.primary(
                      'Save',
                      onPressed: () {
                        final result = _BreatheSettings(
                          preset: _preset,
                          inhaleS: _inh,
                          hold1S: _h1,
                          exhaleS: _exh,
                          hold2S: _h2,
                          haptics: _haptics,
                          targetCycles: _target,
                          tts: _tts,
                        );
                        Navigator.pop(context, result);
                      },
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReadOnlyDurations extends StatelessWidget {
  final int inh, h1, exh, h2;
  const _ReadOnlyDurations({
    required this.inh,
    required this.h1,
    required this.exh,
    required this.h2,
  });

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context)
        .textTheme
        .bodyMedium
        ?.copyWith(fontWeight: FontWeight.w700);

    return Row(
      children: [
        Expanded(child: _pill('Inhale', '$inh s', style)),
        const SizedBox(width: 8),
        Expanded(child: _pill('Hold 1', '$h1 s', style)),
        const SizedBox(width: 8),
        Expanded(child: _pill('Exhale', '$exh s', style)),
        const SizedBox(width: 8),
        Expanded(child: _pill('Hold 2', '$h2 s', style)),
      ],
    );
  }

  Widget _pill(String label, String value, TextStyle? style) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(
        children: [
          Text(label,
              style: const TextStyle(color: Color(0xFF334155), fontSize: 12)),
          const SizedBox(height: 4),
          Text(value, style: style),
        ],
      ),
    );
  }
}

class _LabeledSlider extends StatelessWidget {
  final String label;
  final double value;
  final double min, max;
  final int? divisions;
  final ValueChanged<double> onChanged;

  const _LabeledSlider({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.onChanged,
    this.divisions,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$label: ${value.round()}s',
            style: Theme.of(context).textTheme.labelLarge),
        Slider(
          value: value,
          onChanged: onChanged,
          min: min,
          max: max,
          divisions: divisions,
        ),
      ],
    );
  }
}
