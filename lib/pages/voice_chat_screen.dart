// lib/pages/voice_chat_screen.dart
import 'dart:async';


import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:uuid/uuid.dart';

import 'package:mindcore_ai/services/chat_stream_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

enum _VoiceState { idle, listening, thinking, speaking }

class _VoiceChatScreenState extends State<VoiceChatScreen>
    with TickerProviderStateMixin {
  final _stt = SpeechToText();
  final _uuid = const Uuid();

  _VoiceState _state = _VoiceState.idle;
  bool _sttReady = false;
  String _moodLabel = 'calm';

  // Conversation history for context
  final List<Map<String, String>> _history = [];

  // Animation controllers
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late Animation<double> _pulseAnim;

  // Voice minutes tracking
  Timer? _voiceTimer;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    )..repeat(reverse: true);

    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..repeat(reverse: true);

    _pulseAnim = Tween<double>(begin: 0.92, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _initStt();
    _checkAccess();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _waveController.dispose();
    _voiceTimer?.cancel();
    UsageService.instance.flushVoiceBuffer();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  Future<void> _checkAccess() async {
    final ok = await PremiumService.checkAndPrompt(context);
    if (!ok && mounted) Navigator.of(context).pop();
  }

  Future<void> _initStt() async {
    final available = await _stt.initialize(
      onError: (e) => debugPrint('STT error: $e'),
    );
    if (mounted) setState(() => _sttReady = available);
  }

  // ── Hold to speak ──────────────────────────────────────────────────────

  Future<void> _onHold() async {
    if (!_sttReady || _state != _VoiceState.idle) return;

    // Check voice limit
    final allowed = await UsageService.instance.tryConsumeVoice(context);
    if (!allowed) return;

    await OpenAiTtsService.instance.stop();

    setState(() => _state = _VoiceState.listening);
    _startVoiceTimer();

    await _stt.listen(
      onResult: (_) {},
      listenOptions: SpeechListenOptions(
        listenMode: ListenMode.dictation,
        cancelOnError: true,
      ),
    );
    return;
  }

  Future<void> _onRelease() async {
  if (_state != _VoiceState.listening) {
    return;
  }

  _stopVoiceTimer();

  // Give STT a moment to finalise the last word
  await Future.delayed(const Duration(milliseconds: 500));
  await _stt.stop();

  // Wait up to 2 seconds for final recognised words
  int waited = 0;
  while (_stt.lastRecognizedWords.isEmpty && waited < 2000) {
    await Future.delayed(const Duration(milliseconds: 100));
    waited += 100;
  }

  final spoken = _stt.lastRecognizedWords.trim();

  debugPrint('VoiceChat — recognised: "$spoken"');

  if (spoken.isEmpty) {
    if (mounted) setState(() => _state = _VoiceState.idle);
    return;
  }

  if (mounted) setState(() => _state = _VoiceState.thinking);
  await _sendToAI(spoken);
  return;
}

  // ── AI call ────────────────────────────────────────────────────────────

  Future<void> _sendToAI(String userText) async {
  _history.add({'role': 'user', 'content': userText});

  try {
    final result = await ChatStreamService.streamOrchestratedReply(
      history: _history,
      moodLabel: _moodLabel,
      userInput: userText,
      screen: 'voice',
      onDelta: (delta) async {},
    );

    final reply = result.reply.trim();
    if (reply.isEmpty) {
      if (mounted) setState(() => _state = _VoiceState.idle);
      return;
    }

    _history.add({'role': 'assistant', 'content': reply});

    _moodLabel = result.supportModeLabel.toLowerCase().contains('reset')
        ? 'anxious'
        : result.supportModeLabel.toLowerCase().contains('sleep')
            ? 'low'
            : 'calm';

    if (!mounted) return;
    setState(() => _state = _VoiceState.speaking);

    // Small delay to let state update before TTS starts
    await Future.delayed(const Duration(milliseconds: 200));

    await OpenAiTtsService.instance.speak(
      reply,
      moodLabel: _moodLabel,
      messageId: _uuid.v4(),
      surface: TtsSurface.chat,
      force: true,
    );

    // Wait for TTS to actually start then finish
    await Future.delayed(const Duration(milliseconds: 500));
    await _waitForTtsToFinish();

    if (mounted) setState(() => _state = _VoiceState.idle);
  } catch (e) {
    debugPrint('VoiceChat error: $e');
    if (mounted) setState(() => _state = _VoiceState.idle);
  }
  return;
}

  Future<void> _waitForTtsToFinish() async {
    while (OpenAiTtsService.instance.isSpeakingNow) {
      await Future.delayed(const Duration(milliseconds: 200));
      if (!mounted) return;
    }
  }

  // ── Voice minute tracking ──────────────────────────────────────────────

  void _startVoiceTimer() {
    _voiceTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      final stillOk = await UsageService.instance.recordVoiceSecond();
      if (!stillOk && mounted) {
        // Ran out of minutes mid-session
        await _onRelease();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Voice minutes used up for this month.'),
          ),
        );
      }
    });
  }

  void _stopVoiceTimer() {
    _voiceTimer?.cancel();
    _voiceTimer = null;
  }

  // ── Minutes display ────────────────────────────────────────────────────

  String get _minutesLabel {
    final snap = UsageService.instance.snapshot.value;
    if (snap.tier.monthlyVoiceSeconds == -1) return 'Unlimited';
    final rem = snap.voiceMinutesRemaining;
    return '$rem min left';
  }

  // ── UI ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white54),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          ValueListenableBuilder(
            valueListenable: UsageService.instance.snapshot,
            builder: (_, snap, __) => Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(
                  _minutesLabel,
                  style: const TextStyle(
                    color: Colors.white38,
                    fontSize: 12,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Spacer(),
              Center(child: _buildCentralOrb()),
              const SizedBox(height: 48),
              Center(child: _buildStateLabel()),
              const Spacer(),
              Center(child: _buildHoldButton()),
          ]   

        ),
      ),
    );
  }

  Widget _buildCentralOrb() {
    final color = _stateColor();

    return AnimatedBuilder(
      animation: Listenable.merge([_pulseController, _waveController]),
      builder: (_, __) {
        return SizedBox(
          width: 220,
          height: 220,
          child: Stack(
            alignment: Alignment.center,
            children: [
              // Outer ring glow
              if (_state == _VoiceState.listening ||
                  _state == _VoiceState.speaking)
                ..._buildWaveRings(color),

              // Idle pulse ring
              if (_state == _VoiceState.idle)
                Transform.scale(
                  scale: _pulseAnim.value,
                  child: Container(
                    width: 160,
                    height: 160,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: color.withValues(alpha: 0.25),
                        width: 1.5,
                      ),
                    ),
                  ),
                ),

              // Core orb
              AnimatedContainer(
                duration: const Duration(milliseconds: 400),
                width: _state == _VoiceState.listening ? 120 : 100,
                height: _state == _VoiceState.listening ? 120 : 100,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color.withValues(alpha: 0.15),
                  border: Border.all(
                    color: color.withValues(alpha: 0.6),
                    width: 2,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: color.withValues(alpha: 0.3),
                      blurRadius: 40,
                      spreadRadius: 8,
                    ),
                  ],
                ),
                child: Center(
                  child: AnimatedSwitcher(
                    duration: const Duration(milliseconds: 300),
                    child: _buildOrbIcon(),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _buildWaveRings(Color color) {
    return List.generate(3, (i) {
      final scale = 1.0 +
          (i * 0.18) +
          (_waveController.value * 0.12 * (i + 1));
      final opacity = (0.18 - i * 0.05).clamp(0.0, 1.0);
      return Transform.scale(
        scale: scale,
        child: Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: color.withValues(alpha: opacity),
              width: 1.5,
            ),
          ),
        ),
      );
    });
  }

  Widget _buildOrbIcon() {
  switch (_state) {
    case _VoiceState.idle:
      return ClipOval(
        child: Image.asset(
          'assets/images/logo512.png',
          width: 52,
          height: 52,
          fit: BoxFit.cover,
          key: const ValueKey('idle'),
        ),
      );
    case _VoiceState.listening:
      return ClipOval(
        child: Image.asset(
          'assets/images/logo512.png',
          width: 58,
          height: 58,
          fit: BoxFit.cover,
          key: const ValueKey('listening'),
        ),
      );
    case _VoiceState.thinking:
      return const SizedBox(
        key: ValueKey('thinking'),
        width: 28,
        height: 28,
        child: CircularProgressIndicator(
          strokeWidth: 2,
          color: Colors.white70,
        ),
      );
    case _VoiceState.speaking:
      return ClipOval(
        child: Image.asset(
          'assets/images/logo512.png',
          width: 52,
          height: 52,
          fit: BoxFit.cover,
          key: const ValueKey('speaking'),
        ),
      );
  }
}

  Color _stateColor() {
    switch (_state) {
      case _VoiceState.idle:
        return const Color(0xFF4D7CFF);
      case _VoiceState.listening:
        return const Color(0xFF32D0BE);
      case _VoiceState.thinking:
        return const Color(0xFF9B7FFF);
      case _VoiceState.speaking:
        return const Color(0xFF4D7CFF);
    }
  }

  Widget _buildStateLabel() {
    String label;
    switch (_state) {
      case _VoiceState.idle:
        label = 'Hold to speak';
        break;
      case _VoiceState.listening:
        label = 'Listening…';
        break;
      case _VoiceState.thinking:
        label = 'Thinking…';
        break;
      case _VoiceState.speaking:
        label = 'Speaking…';
        break;
    }

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(
        label,
        key: ValueKey(label),
        style: const TextStyle(
          color: Colors.white38,
          fontSize: 15,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  Widget _buildHoldButton() {
    final isListening = _state == _VoiceState.listening;

    return GestureDetector(
      onTapDown: (_) => _onHold(),
      onTapUp: (_) => _onRelease(),
      onTapCancel: () => _onRelease(),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: isListening ? 80 : 72,
        height: isListening ? 80 : 72,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isListening
              ? const Color(0xFF32D0BE).withValues(alpha: 0.2)
              : Colors.white.withValues(alpha: 0.06),
          border: Border.all(
            color: isListening
                ? const Color(0xFF32D0BE).withValues(alpha: 0.8)
                : Colors.white.withValues(alpha: 0.15),
            width: isListening ? 2 : 1,
          ),
        ),
        child: Icon(
          isListening ? Icons.stop_rounded : Icons.mic_rounded,
          color: isListening
              ? const Color(0xFF32D0BE)
              : Colors.white.withValues(alpha: 0.6),
          size: 30,
        ),
      ),
    );
  }
}