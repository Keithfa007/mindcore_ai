// lib/pages/breathe_screen.dart
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../widgets/page_scaffold.dart';
import '../widgets/app_top_bar.dart';
import '../widgets/surfaces.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/ai_breathing_coach_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';

enum _Phase { inhale, hold1, exhale, hold2 }
enum _Preset { box, equal, fourSevenEight, custom }

class _BreatheSettings {
  final _Preset preset;
  final int inhaleS, hold1S, exhaleS, hold2S;
  final bool haptics;
  final int targetCycles;
  final bool tts;
  const _BreatheSettings({
    required this.preset,
    required this.inhaleS, required this.hold1S,
    required this.exhaleS, required this.hold2S,
    required this.haptics, required this.targetCycles, required this.tts,
  });
  _BreatheSettings copyWith({_Preset? preset, int? inhaleS, int? hold1S,
      int? exhaleS, int? hold2S, bool? haptics, int? targetCycles, bool? tts}) {
    return _BreatheSettings(
      preset: preset ?? this.preset, inhaleS: inhaleS ?? this.inhaleS,
      hold1S: hold1S ?? this.hold1S, exhaleS: exhaleS ?? this.exhaleS,
      hold2S: hold2S ?? this.hold2S, haptics: haptics ?? this.haptics,
      targetCycles: targetCycles ?? this.targetCycles, tts: tts ?? this.tts,
    );
  }
}

class _BreathePrefs {
  static const _kPreset = 'breathe_preset_v1';
  static const _kInhale = 'breathe_inhale_s_v1';
  static const _kHold1  = 'breathe_hold1_s_v1';
  static const _kExhale = 'breathe_exhale_s_v1';
  static const _kHold2  = 'breathe_hold2_s_v1';
  static const _kHapt   = 'breathe_haptics_v1';
  static const _kTarget = 'breathe_target_cycles_v1';
  static const _kTts    = 'breathe_tts_v1';
  static const _default = _BreatheSettings(
    preset: _Preset.box, inhaleS: 4, hold1S: 4, exhaleS: 4, hold2S: 4,
    haptics: true, targetCycles: 0, tts: true,
  );
  static Future<_BreatheSettings> load() async {
    final p = await SharedPreferences.getInstance();
    final preset = <String, _Preset>{
      'box': _Preset.box, 'equal': _Preset.equal,
      '478': _Preset.fourSevenEight, 'custom': _Preset.custom,
    }[p.getString(_kPreset) ?? 'box'] ?? _Preset.box;
    return _BreatheSettings(
      preset: preset,
      inhaleS: p.getInt(_kInhale) ?? _default.inhaleS,
      hold1S:  p.getInt(_kHold1)  ?? _default.hold1S,
      exhaleS: p.getInt(_kExhale) ?? _default.exhaleS,
      hold2S:  p.getInt(_kHold2)  ?? _default.hold2S,
      haptics: p.getBool(_kHapt)  ?? _default.haptics,
      targetCycles: p.getInt(_kTarget) ?? _default.targetCycles,
      tts: p.getBool(_kTts) ?? _default.tts,
    );
  }
  static Future<void> save(_BreatheSettings s) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_kPreset, <_Preset, String>{
      _Preset.box: 'box', _Preset.equal: 'equal',
      _Preset.fourSevenEight: '478', _Preset.custom: 'custom',
    }[s.preset]!);
    await p.setInt(_kInhale, s.inhaleS); await p.setInt(_kHold1, s.hold1S);
    await p.setInt(_kExhale, s.exhaleS); await p.setInt(_kHold2, s.hold2S);
    await p.setBool(_kHapt, s.haptics);
    await p.setInt(_kTarget, s.targetCycles);
    await p.setBool(_kTts, s.tts);
  }
}

class BreatheScreen extends StatefulWidget {
  const BreatheScreen({super.key});
  @override
  State<BreatheScreen> createState() => _BreatheScreenState();
}

class _BreatheScreenState extends State<BreatheScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;
  late Duration _dInhale, _dHold1, _dExhale, _dHold2;
  Duration get _cycle => _dInhale + _dHold1 + _dExhale + _dHold2;

  _BreatheSettings _settings = _BreathePrefs._default;
  bool _running = false;
  int _completedCycles = 0;
  final ValueNotifier<_Phase> _phaseVN = ValueNotifier<_Phase>(_Phase.inhale);
  final ValueNotifier<int> _cyclesVN  = ValueNotifier<int>(0);
  _Phase? _lastSpokenPhase;
  bool _aiCoachEnabled = true;
  bool _loadingCoach   = false;
  String _coachMoodLabel = 'calm';
  AiBreathingCoachPlan _coachPlan = AiBreathingCoachPlan.fallback('calm');
  double _lastAnimValue = 0.0;

  @override
  void initState() {
    super.initState();
    _applyDurationsFrom(_settings);
    _c = AnimationController(vsync: this, duration: _cycle)
      ..addListener(_onTick);
    _loadSettings();
    _loadCoachPref();
    WidgetsBinding.instance
        .addPostFrameCallback((_) => _checkPremiumAccess());
  }

  Future<void> _checkPremiumAccess() async {
    if (!mounted) return;
    if (PremiumService.isPremium.value) return;
    await Navigator.of(context).pushNamed('/paywall');
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      Navigator.of(context)
          .pushNamedAndRemoveUntil('/home', (route) => false);
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
    _aiCoachEnabled =
        await LiveVoicePreferences.getAiBreathingCoachEnabled();
    if (mounted) setState(() {});
  }

  String get _presetName {
    switch (_settings.preset) {
      case _Preset.box:          return 'Box';
      case _Preset.equal:        return 'Equal';
      case _Preset.fourSevenEight: return '4-7-8';
      case _Preset.custom:       return 'Custom';
    }
  }

  Future<void> _prepareAiCoach() async {
    if (!_aiCoachEnabled) return;
    setState(() => _loadingCoach = true);
    final plan = await AiBreathingCoachService.buildPlan(
        moodLabel: _coachMoodLabel, presetName: _presetName);
    if (!mounted) return;
    setState(() { _coachPlan = plan; _loadingCoach = false; });
  }

  void _applyDurationsFrom(_BreatheSettings s) {
    _dInhale = Duration(seconds: s.inhaleS);
    _dHold1  = Duration(seconds: s.hold1S);
    _dExhale = Duration(seconds: s.exhaleS);
    _dHold2  = Duration(seconds: s.hold2S);
  }

  void _stopWithTargetReached() {
    _running = false; _c.stop(); OpenAiTtsService.instance.stop();
    if (_settings.haptics) HapticFeedback.mediumImpact();
    if (mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Session complete')));
      setState(() {});
    }
  }

  void _onTick() {
    if (_running && _c.value < _lastAnimValue) {
      _completedCycles++;
      _cyclesVN.value = _completedCycles;
      if (_settings.targetCycles > 0 &&
          _completedCycles >= _settings.targetCycles) {
        _stopWithTargetReached();
        _lastAnimValue = _c.value;
        return;
      }
    }
    _lastAnimValue = _c.value;
    final t = _c.value * _cycle.inMilliseconds;
    final a = _dInhale.inMilliseconds;
    final b = _dHold1.inMilliseconds;
    final c = _dExhale.inMilliseconds;
    _Phase next;
    if (t < a)         next = _Phase.inhale;
    else if (t < a+b)  next = _Phase.hold1;
    else if (t < a+b+c) next = _Phase.exhale;
    else               next = _Phase.hold2;
    if (next != _phaseVN.value) {
      _phaseVN.value = next;
      if (_settings.haptics) HapticFeedback.lightImpact();
      _speakPhase(next);
    }
  }

  Future<void> _speakPhase(_Phase p) async {
    if (!_settings.tts || !_running || _lastSpokenPhase == p) return;
    _lastSpokenPhase = p;
    String text;
    switch (p) {
      case _Phase.inhale: text = _aiCoachEnabled ? _coachPlan.inhale : 'Inhale'; break;
      case _Phase.exhale: text = _aiCoachEnabled ? _coachPlan.exhale : 'Exhale'; break;
      case _Phase.hold1: case _Phase.hold2:
        text = _aiCoachEnabled ? _coachPlan.hold : 'Hold'; break;
    }
    await OpenAiTtsService.instance.speak(
      text, moodLabel: 'calm',
      messageId: 'breathe_phase', surface: TtsSurface.breathe,
    );
  }

  @override
  void dispose() {
    _c.dispose(); _phaseVN.dispose(); _cyclesVN.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  void _toggle() async {
    if (_running) {
      _c.stop(); OpenAiTtsService.instance.stop();
      setState(() => _running = false);
      return;
    }
    _completedCycles = 0;
    _coachMoodLabel = _settings.tts ? 'calm' : 'neutral';
    await _prepareAiCoach();
    _cyclesVN.value = 0; _lastSpokenPhase = null;
    _c.duration = _cycle; _lastAnimValue = _c.value;
    _c.repeat(period: _cycle);
    if (_aiCoachEnabled && _settings.tts && _coachPlan.intro.isNotEmpty) {
      await OpenAiTtsService.instance.speak(
        _coachPlan.intro, moodLabel: 'calm',
        messageId: 'breathe_intro', surface: TtsSurface.breathe,
      );
    }
    _speakPhase(_phaseVN.value);
    setState(() => _running = true);
  }

  void _reset() {
    _c.stop(); _c.value = 0; _running = false;
    _completedCycles = 0; _cyclesVN.value = 0;
    _phaseVN.value = _Phase.inhale; _lastSpokenPhase = null;
    _lastAnimValue = 0.0;
    OpenAiTtsService.instance.stop();
    setState(() {});
  }

  Future<void> _openSettings() async {
    final updated = await showModalBottomSheet<_BreatheSettings>(
      context: context, isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surface,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (ctx) => _BreatheSettingsSheet(initial: _settings),
    );
    if (updated == null || !mounted) return;
    await _BreathePrefs.save(updated);
    setState(() {
      _settings = updated; _applyDurationsFrom(_settings);
      _c.duration = _cycle; _c.stop(); _c.value = 0.0;
      _completedCycles = 0; _cyclesVN.value = 0;
      _phaseVN.value = _Phase.inhale; _lastSpokenPhase = null;
      _lastAnimValue = 0.0;
      if (_running) {
        _c.repeat(period: _cycle); _speakPhase(_phaseVN.value);
      } else {
        OpenAiTtsService.instance.stop();
      }
    });
  }

  // ── Helpers ─────────────────────────────────────────────────────

  String _phaseLabel(_Phase p) {
    switch (p) {
      case _Phase.inhale: return 'INHALE';
      case _Phase.hold1:  return 'HOLD';
      case _Phase.exhale: return 'EXHALE';
      case _Phase.hold2:  return 'HOLD';
    }
  }

  String _phaseGuidance(_Phase p) {
    switch (p) {
      case _Phase.inhale: return 'Breathe in gently through your nose';
      case _Phase.hold1:  return 'Hold — stay calm and still';
      case _Phase.exhale: return 'Breathe out slowly through your mouth';
      case _Phase.hold2:  return 'Hold — prepare for next breath';
    }
  }

  Color _phaseColor(_Phase p) {
    switch (p) {
      case _Phase.inhale: return AppColors.primary;
      case _Phase.hold1:  return AppColors.mintDeep;
      case _Phase.exhale: return AppColors.violet;
      case _Phase.hold2:  return AppColors.primary;
    }
  }

  double _phaseLocalProgress() {
    final ms = _c.value * _cycle.inMilliseconds;
    final a = _dInhale.inMilliseconds;
    final b = _dHold1.inMilliseconds;
    final c = _dExhale.inMilliseconds;
    final d = _dHold2.inMilliseconds;
    double safeDiv(double num, int den) =>
        den == 0 ? 1.0 : (num / den).clamp(0.0, 1.0);
    if (ms < a)       return safeDiv(ms, a);
    if (ms < a+b)     return safeDiv(ms-a, b);
    if (ms < a+b+c)   return safeDiv(ms-a-b, c);
    return safeDiv(ms-a-b-c, d);
  }

  double _orbScale() {
    final p = _phaseLocalProgress();
    final phase = _phaseVN.value;
    switch (phase) {
      case _Phase.inhale:
        return _lerp(0.58, 1.0, Curves.easeOut.transform(p));
      case _Phase.hold1:
        return 1.0;
      case _Phase.exhale:
        return _lerp(1.0, 0.58, Curves.easeIn.transform(p));
      case _Phase.hold2:
        return 0.58;
    }
  }

  int _phaseSecondsLeft() {
    final ms = _c.value * _cycle.inMilliseconds;
    final a = _dInhale.inMilliseconds.toDouble();
    final b = _dHold1.inMilliseconds.toDouble();
    final c = _dExhale.inMilliseconds.toDouble();
    final d = _dHold2.inMilliseconds.toDouble();
    double remaining;
    if (ms < a)         remaining = a - ms;
    else if (ms < a+b)  remaining = a + b - ms;
    else if (ms < a+b+c) remaining = a + b + c - ms;
    else                remaining = a + b + c + d - ms;
    return ((remaining / 1000).ceil()).clamp(0, 99);
  }

  double _lerp(double a, double b, double t) => a + (b - a) * t;

  // ── Build ────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs     = Theme.of(context).colorScheme;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Breathe'),
      bottomIndex: 2,
      body: AnimatedBackdrop(
        child: SafeArea(
          top: false,
          child: Column(
            children: [

              // ── Top bar row ────────────────────────────────────────
              Padding(
                padding:
                    const EdgeInsets.fromLTRB(20, 12, 12, 0),
                child: Row(
                  children: [
                    // Preset + cycle count
                    ValueListenableBuilder<int>(
                      valueListenable: _cyclesVN,
                      builder: (_, cycles, __) => Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '$_presetName breathing',
                            style: tt.labelSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              letterSpacing: 0.5,
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.50)
                                  : Colors.black.withValues(alpha: 0.40),
                            ),
                          ),
                          Text(
                            '$cycles cycle${cycles == 1 ? '' : 's'}'
                            '${_settings.targetCycles > 0 ? ' / ${_settings.targetCycles}' : ''}',
                            style: tt.bodySmall?.copyWith(
                              fontWeight: FontWeight.w800,
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.70)
                                  : Colors.black.withValues(alpha: 0.60),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Spacer(),
                    // Voice cue indicator
                    if (_settings.tts)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppColors.mintDeep.withValues(alpha: 0.10),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color:
                                  AppColors.mintDeep.withValues(alpha: 0.30)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.record_voice_over_rounded,
                                size: 12, color: AppColors.mintDeep),
                            const SizedBox(width: 4),
                            Text('Voice on',
                                style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w700,
                                    color: AppColors.mintDeep)),
                          ],
                        ),
                      ),
                    const SizedBox(width: 8),
                    IconButton(
                      icon: const Icon(Icons.tune_rounded),
                      tooltip: 'Settings',
                      onPressed: _openSettings,
                    ),
                  ],
                ),
              ),

              // ── Breathing orb ──────────────────────────────────────
              Expanded(
                child: Center(
                  child: AnimatedBuilder(
                    animation: _c,
                    builder: (_, __) {
                      final scale    = _running ? _orbScale() : 0.70;
                      final progress = _running ? _phaseLocalProgress() : 0.0;
                      final phase    = _phaseVN.value;
                      final color    = _phaseColor(phase);
                      final secsLeft = _running ? _phaseSecondsLeft() : 0;

                      return SizedBox(
                        width: 290,
                        height: 290,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            // Outermost glow
                            Transform.scale(
                              scale: scale * 1.50,
                              child: Container(
                                width: 200,
                                height: 200,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: color.withValues(alpha: 0.04),
                                ),
                              ),
                            ),
                            // Middle glow
                            Transform.scale(
                              scale: scale * 1.25,
                              child: Container(
                                width: 200,
                                height: 200,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: color.withValues(alpha: 0.07),
                                ),
                              ),
                            ),
                            // Arc progress ring
                            if (_running)
                              CustomPaint(
                                size: const Size(290, 290),
                                painter: _ArcPainter(
                                    progress: progress, color: color),
                              ),
                            // Main orb
                            Transform.scale(
                              scale: scale,
                              child: Container(
                                width: 200,
                                height: 200,
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: RadialGradient(
                                    colors: [
                                      color.withValues(alpha: 0.65),
                                      color.withValues(alpha: 0.28),
                                      color.withValues(alpha: 0.05),
                                    ],
                                    stops: const [0.0, 0.55, 1.0],
                                  ),
                                  border: Border.all(
                                      color: color.withValues(alpha: 0.45),
                                      width: 1.5),
                                ),
                              ),
                            ),
                            // Center content
                            Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                if (_running) ...[
                                  Text(
                                    '$secsLeft',
                                    style: const TextStyle(
                                      fontSize: 58,
                                      fontWeight: FontWeight.w200,
                                      color: Colors.white,
                                      height: 1.0,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _phaseLabel(phase),
                                    style: const TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.w700,
                                      color: Colors.white,
                                      letterSpacing: 2.5,
                                    ),
                                  ),
                                ] else
                                  Icon(
                                    Icons.air_rounded,
                                    size: 44,
                                    color:
                                        Colors.white.withValues(alpha: 0.60),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
              ),

              // ── Phase guidance text ─────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: ValueListenableBuilder<_Phase>(
                  valueListenable: _phaseVN,
                  builder: (_, phase, __) => AnimatedSwitcher(
                    duration: const Duration(milliseconds: 350),
                    transitionBuilder: (child, anim) =>
                        FadeTransition(opacity: anim, child: child),
                    child: Column(
                      key: ValueKey(phase),
                      children: [
                        Text(
                          _running ? _phaseGuidance(phase) : 'Tap start when you are ready',
                          textAlign: TextAlign.center,
                          style: tt.bodyMedium?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.55)
                                : Colors.black.withValues(alpha: 0.50),
                            height: 1.5,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 6),

              // ── Timing pills ────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _TimingPill(
                        label: 'Inhale', seconds: _settings.inhaleS,
                        color: AppColors.primary, isDark: isDark, tt: tt),
                    if (_settings.hold1S > 0) ...[
                      const SizedBox(width: 6),
                      _TimingPill(
                          label: 'Hold', seconds: _settings.hold1S,
                          color: AppColors.mintDeep, isDark: isDark, tt: tt),
                    ],
                    const SizedBox(width: 6),
                    _TimingPill(
                        label: 'Exhale', seconds: _settings.exhaleS,
                        color: AppColors.violet, isDark: isDark, tt: tt),
                    if (_settings.hold2S > 0) ...[
                      const SizedBox(width: 6),
                      _TimingPill(
                          label: 'Hold', seconds: _settings.hold2S,
                          color: AppColors.primary, isDark: isDark, tt: tt),
                    ],
                  ],
                ),
              ),

              const SizedBox(height: 20),

              // ── Controls ────────────────────────────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                child: Row(
                  children: [
                    Expanded(
                      flex: 3,
                      child: GradientButton.primary(
                        _loadingCoach
                            ? 'Preparing…'
                            : (_running ? 'Pause' : 'Start'),
                        onPressed: _loadingCoach ? null : _toggle,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 1,
                      child: SizedBox(
                        height: 52,
                        child: OutlinedButton(
                          onPressed: _reset,
                          style: OutlinedButton.styleFrom(
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14)),
                          ),
                          child: const Icon(Icons.refresh_rounded, size: 20),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ── Arc progress painter ──────────────────────────────────────────────────────

class _ArcPainter extends CustomPainter {
  final double progress;
  final Color color;
  const _ArcPainter({required this.progress, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 5;

    // Track
    final track = Paint()
      ..color = color.withValues(alpha: 0.15)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.5
      ..strokeCap = StrokeCap.round;
    canvas.drawCircle(center, radius, track);

    // Progress arc
    if (progress > 0) {
      final arc = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3.5
        ..strokeCap = StrokeCap.round;
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2,
        2 * math.pi * progress,
        false,
        arc,
      );
    }
  }

  @override
  bool shouldRepaint(_ArcPainter old) =>
      old.progress != progress || old.color != color;
}

// ── Timing pill ───────────────────────────────────────────────────────────────

class _TimingPill extends StatelessWidget {
  final String label;
  final int seconds;
  final Color color;
  final bool isDark;
  final TextTheme tt;
  const _TimingPill({
    required this.label, required this.seconds, required this.color,
    required this.isDark, required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: isDark ? 0.12 : 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.30)),
      ),
      child: Column(
        children: [
          Text('${seconds}s',
              style: TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w900, color: color)),
          Text(label,
              style: tt.bodySmall?.copyWith(
                  fontSize: 10, color: color.withValues(alpha: 0.75))),
        ],
      ),
    );
  }
}

// ── Settings sheet ────────────────────────────────────────────────────────────

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
    _preset  = widget.initial.preset;
    _inh     = widget.initial.inhaleS;
    _h1      = widget.initial.hold1S;
    _exh     = widget.initial.exhaleS;
    _h2      = widget.initial.hold2S;
    _haptics = widget.initial.haptics;
    _target  = widget.initial.targetCycles;
    _tts     = widget.initial.tts;
  }

  void _applyPreset(_Preset p) {
    setState(() {
      _preset = p;
      switch (p) {
        case _Preset.box:          _inh=4; _h1=4; _exh=4; _h2=4; break;
        case _Preset.equal:        _inh=5; _h1=0; _exh=5; _h2=0; break;
        case _Preset.fourSevenEight: _inh=4; _h1=7; _exh=8; _h2=0; break;
        case _Preset.custom: break;
      }
    });
  }

  Widget _chip(String label, _Preset value) => ChoiceChip(
    label: Text(label),
    selected: _preset == value,
    onSelected: (_) => _applyPreset(value),
  );

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;
    return Padding(
      padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40, height: 4,
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                      color: cs.outlineVariant,
                      borderRadius: BorderRadius.circular(2)),
                ),
              ),
              Text('Breathing settings',
                  style: tt.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
              const SizedBox(height: 16),
              Text('Technique',
                  style: tt.labelLarge?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 6, children: [
                _chip('Box 4-4-4-4', _Preset.box),
                _chip('Equal 5-5', _Preset.equal),
                _chip('4-7-8', _Preset.fourSevenEight),
                _chip('Custom', _Preset.custom),
              ]),
              const SizedBox(height: 16),
              if (_preset == _Preset.custom) ...[
                _LabeledSlider(label: 'Inhale', value: _inh.toDouble(),
                    min: 1, max: 12, divisions: 11,
                    onChanged: (v) => setState(() => _inh = v.round())),
                _LabeledSlider(label: 'Hold 1', value: _h1.toDouble(),
                    min: 0, max: 12, divisions: 12,
                    onChanged: (v) => setState(() => _h1 = v.round())),
                _LabeledSlider(label: 'Exhale', value: _exh.toDouble(),
                    min: 1, max: 16, divisions: 15,
                    onChanged: (v) => setState(() => _exh = v.round())),
                _LabeledSlider(label: 'Hold 2', value: _h2.toDouble(),
                    min: 0, max: 12, divisions: 12,
                    onChanged: (v) => setState(() => _h2 = v.round())),
              ] else
                _ReadOnlyDurations(inh: _inh, h1: _h1, exh: _exh, h2: _h2),
              const SizedBox(height: 8),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Haptic feedback'),
                subtitle: const Text('Vibrate on phase change'),
                value: _haptics,
                onChanged: (v) => setState(() => _haptics = v),
              ),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Voice cues'),
                subtitle: const Text('Speaks Inhale / Hold / Exhale'),
                value: _tts,
                onChanged: (v) => setState(() => _tts = v),
              ),
              _LabeledSlider(
                label: 'Target cycles (0 = infinite)',
                value: _target.toDouble(), min: 0, max: 12, divisions: 12,
                onChanged: (v) => setState(() => _target = v.round()),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Padding(
                        padding: EdgeInsets.symmetric(vertical: 14),
                        child: Text('Cancel')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: () => Navigator.pop(
                      context,
                      _BreatheSettings(
                        preset: _preset, inhaleS: _inh, hold1S: _h1,
                        exhaleS: _exh, hold2S: _h2, haptics: _haptics,
                        targetCycles: _target, tts: _tts,
                      ),
                    ),
                    child: const Padding(
                        padding: EdgeInsets.symmetric(vertical: 14),
                        child: Text('Save')),
                  ),
                ),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReadOnlyDurations extends StatelessWidget {
  final int inh, h1, exh, h2;
  const _ReadOnlyDurations(
      {required this.inh, required this.h1, required this.exh, required this.h2});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context)
        .textTheme
        .bodyMedium
        ?.copyWith(fontWeight: FontWeight.w700);
    return Row(children: [
      Expanded(child: _pill('Inhale', '${inh}s', style)),
      const SizedBox(width: 6),
      Expanded(child: _pill('Hold 1', '${h1}s', style)),
      const SizedBox(width: 6),
      Expanded(child: _pill('Exhale', '${exh}s', style)),
      const SizedBox(width: 6),
      Expanded(child: _pill('Hold 2', '${h2}s', style)),
    ]);
  }

  Widget _pill(String label, String value, TextStyle? style) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Column(children: [
        Text(label,
            style:
                const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
        const SizedBox(height: 3),
        Text(value, style: style),
      ]),
    );
  }
}

class _LabeledSlider extends StatelessWidget {
  final String label;
  final double value, min, max;
  final int? divisions;
  final ValueChanged<double> onChanged;
  const _LabeledSlider({
    required this.label, required this.value,
    required this.min, required this.max,
    required this.onChanged, this.divisions,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$label: ${value.round()}s',
            style: Theme.of(context)
                .textTheme
                .labelLarge
                ?.copyWith(fontWeight: FontWeight.w600)),
        Slider(
          value: value, onChanged: onChanged,
          min: min, max: max, divisions: divisions,
        ),
      ],
    );
  }
}
