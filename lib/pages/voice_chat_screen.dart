// lib/pages/voice_chat_screen.dart
// Voice chat TTS switched from Fish Audio to ElevenLabs — July 2026
import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:uuid/uuid.dart';

import 'package:mindcore_ai/ai/agent_prompts.dart';
import 'package:mindcore_ai/env/env.dart';
import 'package:mindcore_ai/services/chat_stream_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/shared_chat_session.dart';
import 'package:mindcore_ai/services/tts_chunk_coordinator.dart';
import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/services/user_memory_service.dart';

class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});
  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

enum _VoiceState { idle, listening, thinking, speaking }

class _VoiceChatScreenState extends State<VoiceChatScreen>
    with TickerProviderStateMixin {
  final _stt  = SpeechToText();
  final _uuid = const Uuid();

  _VoiceState _state             = _VoiceState.idle;
  bool        _sttReady          = false;
  String      _moodLabel         = 'calm';
  int         _voiceMessageCount = 0;

  // ── TTS pipeline ─────────────────────────────────────────────────────────
  final TtsChunkCoordinator          _coordinator    = TtsChunkCoordinator();
  final AudioPlayer                  _chunkPlayer    = AudioPlayer();
  final Queue<Future<Uint8List?>>    _synthesisQueue = Queue();
  bool _chunkPlaying = false;
  bool _cancelled    = false;

  // ── Animations ───────────────────────────────────────────────────────────
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late Animation<double>   _pulseAnim;
  Timer? _voiceTimer;

  // ── 3am Protocol ──────────────────────────────────────────────────────
  bool get _isThreeAm => AgentPrompts.isThreeAmMode(DateTime.now());

  // Warm amber palette for 3am mode
  static const _amberOrb    = Color(0xFFE8A265);
  static const _amberGlow   = Color(0xFFD4874A);
  static const _amberBorder = Color(0xFFF0B97A);

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 1800))
      ..repeat(reverse: true);
    _waveController = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 800))
      ..repeat(reverse: true);
    _pulseAnim = Tween<double>(begin: 0.92, end: 1.08).animate(
        CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut));
    _initStt();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkAccess();
      _preWarm();
    });
    unawaited(SharedChatSession.instance.ensureLoaded());
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _waveController.dispose();
    _voiceTimer?.cancel();
    _coordinator.cancel();
    _chunkPlayer.dispose();
    UsageService.instance.flushVoiceBuffer();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  // ── Pre-warm ───────────────────────────────────────────────────────────

  Future<void> _preWarm() async {
    try {
      await LiveVoicePreferences.instance.load();
      await _chunkPlayer.setVolume(1.0);
      final key = Env.elevenLabsKey;
      if (key.isEmpty) return;
      await http.post(
        Uri.parse('https://api.elevenlabs.io/v1/text-to-speech/${LiveVoicePreferences.instance.activeVoiceId}'),
        headers: {
          'xi-api-key': key,
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg',
        },
        body: jsonEncode({
          'text': 'hi',
          'model_id': 'eleven_multilingual_v2',
          'voice_settings': {
            'stability': 0.45,
            'similarity_boost': 0.70,
            'style': 0.35,
            'use_speaker_boost': true,
          },
        }),
      ).timeout(const Duration(seconds: 8));
    } catch (_) {}
  }

  // ── TTS synthesis ─────────────────────────────────────────────────────────

  Future<Uint8List?> _synthesise(String text) async {
    try {
      final key     = Env.elevenLabsKey;
      final voiceId = LiveVoicePreferences.instance.activeVoiceId;
      if (key.isEmpty || text.trim().isEmpty) return null;
      final res = await http.post(
        Uri.parse('https://api.elevenlabs.io/v1/text-to-speech/$voiceId'),
        headers: {
          'xi-api-key': key,
          'Content-Type': 'application/json',
          'Accept': 'audio/mpeg',
        },
        body: jsonEncode({
          'text': text.trim(),
          'model_id': 'eleven_multilingual_v2',
          'voice_settings': {
            'stability': 0.45,
            'similarity_boost': 0.70,
            'style': 0.35,
            'use_speaker_boost': true,
          },
        }),
      ).timeout(const Duration(seconds: 15));
      if (res.statusCode != 200) return null;
      return Uint8List.fromList(res.bodyBytes);
    } catch (_) {
      return null;
    }
  }

  // ── Chunk pipeline ──────────────────────────────────────────────────────────

  void _enqueueChunk(String text) {
    if (_cancelled) return;
    if (mounted && _state == _VoiceState.thinking) {
      setState(() => _state = _VoiceState.speaking);
    }
    _synthesisQueue.add(_synthesise(text));
    if (!_chunkPlaying) unawaited(_drainChunks());
  }

  Future<void> _drainChunks() async {
    if (_chunkPlaying) return;
    _chunkPlaying = true;
    try {
      while (_synthesisQueue.isNotEmpty && !_cancelled && mounted) {
        final bytes = await _synthesisQueue.removeFirst();
        if (bytes == null || _cancelled || !mounted) continue;
        try {
          await _chunkPlayer.setAudioSource(
            _BytesSource(bytes, contentType: 'audio/mpeg'),
          );
          final completer = Completer<void>();
          final sub = _chunkPlayer.playerStateStream.listen((s) {
            if (!completer.isCompleted) {
              final done = s.processingState == ProcessingState.completed ||
                  s.processingState == ProcessingState.idle;
              if (done) completer.complete();
            }
          });
          await _chunkPlayer.play();
          await completer.future
              .timeout(const Duration(seconds: 30), onTimeout: () {})
              .catchError((_) {});
          await sub.cancel();
        } catch (_) {}
      }
    } finally {
      _chunkPlaying = false;
      if (mounted && !_cancelled) setState(() => _state = _VoiceState.idle);
    }
  }

  void _cancelAudio() {
    _cancelled = true;
    _coordinator.cancel();
    _synthesisQueue.clear();
    _chunkPlayer.stop();
    _chunkPlaying = false;
  }

  // ── Access / STT ─────────────────────────────────────────────────────────

  Future<void> _checkAccess() async {
    if (!mounted) return;
    if (PremiumService.isPremium.value) return;
    await Navigator.of(context).pushNamed('/paywall');
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (r) => false);
    }
  }

  Future<void> _initStt() async {
    final ok = await _stt.initialize(onError: (e) => debugPrint('STT error: $e'));
    if (mounted) setState(() => _sttReady = ok);
  }

  // ── Hold-to-speak ────────────────────────────────────────────────────────

  Future<void> _onHold() async {
    if (_state == _VoiceState.speaking) {
      _cancelAudio();
      if (mounted) setState(() => _state = _VoiceState.idle);
      return;
    }
    if (!_sttReady || _state != _VoiceState.idle) return;
    final allowed = await UsageService.instance.tryConsumeVoice(context);
    if (!allowed) return;
    _cancelAudio();
    OpenAiTtsService.instance.stop();
    setState(() => _state = _VoiceState.listening);
    _startVoiceTimer();
    await _stt.listen(
      onResult: (_) {},
      pauseFor: const Duration(seconds: 8),
      listenFor: const Duration(minutes: 3),
      listenOptions: SpeechListenOptions(
        listenMode: ListenMode.dictation,
        cancelOnError: false,
      ),
    );
  }

  Future<void> _onRelease() async {
    if (_state != _VoiceState.listening) return;
    _stopVoiceTimer();
    await Future.delayed(const Duration(milliseconds: 500));
    await _stt.stop();
    int waited = 0;
    while (_stt.lastRecognizedWords.isEmpty && waited < 2000) {
      await Future.delayed(const Duration(milliseconds: 100));
      waited += 100;
    }
    final spoken = _stt.lastRecognizedWords.trim();
    if (spoken.isEmpty) {
      if (mounted) setState(() => _state = _VoiceState.idle);
      return;
    }
    if (mounted) setState(() => _state = _VoiceState.thinking);
    await _sendToAI(spoken);
  }

  // ── AI call ────────────────────────────────────────────────────────────────

  Future<void> _sendToAI(String userText) async {
    SharedChatSession.instance.addUser(userText);
    _cancelled = false;
    _synthesisQueue.clear();
    _chunkPlaying = false;

    final sessionId   = _uuid.v4();
    _coordinator.startSession(sessionId);
    final accumulated = StringBuffer();

    try {
      final history = SharedChatSession.instance.historyForAI;
      if (history.isNotEmpty && history.last['role'] == 'user') history.removeLast();

      final result = await ChatStreamService.streamOrchestratedReply(
        history:   history,
        moodLabel: _moodLabel,
        userInput: userText,
        screen:    'voice',
        onDelta: (delta) async {
          if (_cancelled) return;
          accumulated.write(delta);
          _coordinator.ingest(
            sessionId: sessionId,
            fullText:  accumulated.toString(),
            player: (chunk, idx, next) async {
              if (_cancelled) return;
              _enqueueChunk(chunk);
            },
          );
        },
      );

      if (_cancelled) {
        if (mounted) setState(() => _state = _VoiceState.idle);
        return;
      }

      await _coordinator.finish(
        sessionId: sessionId,
        fullText:  result.reply,
        player: (chunk, idx, next) async {
          if (_cancelled) return;
          _enqueueChunk(chunk);
        },
      );

      SharedChatSession.instance.addAssistant(result.reply);

      _voiceMessageCount++;
      if (_voiceMessageCount % 5 == 0) {
        unawaited(UserMemoryService.saveMemory(SharedChatSession.instance.historyForAI));
      }

      _moodLabel = result.supportModeLabel.toLowerCase().contains('reset')
          ? 'anxious'
          : result.supportModeLabel.toLowerCase().contains('sleep')
              ? 'low'
              : 'calm';

      if (_state == _VoiceState.thinking && mounted) {
        setState(() => _state = _VoiceState.idle);
      }
    } catch (e) {
      debugPrint('VoiceChat error: $e');
      if (mounted) setState(() => _state = _VoiceState.idle);
    }
  }

  // ── Voice timer ──────────────────────────────────────────────────────────

  void _startVoiceTimer() {
    _voiceTimer = Timer.periodic(const Duration(seconds: 1), (_) async {
      final ok = await UsageService.instance.recordVoiceSecond();
      if (!ok && mounted) {
        await _onRelease();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Voice minutes used up for this month.')),
        );
      }
    });
  }

  void _stopVoiceTimer() {
    _voiceTimer?.cancel();
    _voiceTimer = null;
  }

  String get _minutesLabel {
    final snap = UsageService.instance.snapshot.value;
    if (snap.tier.monthlyVoiceSeconds == -1) return 'Unlimited';
    return '${snap.voiceMinutesRemaining} min left';
  }

  // ── 3am colours ──────────────────────────────────────────────────────────

  Color _stateColor() {
    if (_isThreeAm) return _amberOrb;
    switch (_state) {
      case _VoiceState.idle:      return const Color(0xFF4D7CFF);
      case _VoiceState.listening: return const Color(0xFF32D0BE);
      case _VoiceState.thinking:  return const Color(0xFF9B7FFF);
      case _VoiceState.speaking:  return const Color(0xFF4D7CFF);
    }
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final threeAm = _isThreeAm;
    return Scaffold(
      backgroundColor: threeAm
          ? const Color(0xFF0D0A07)  // warmer dark for 3am
          : const Color(0xFF0A0E1A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.white54),
          onPressed: () => Navigator.of(context).pop(),
        ),
        actions: [
          // Moon icon — visible only in 3am mode
          if (threeAm)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Center(
                child: Text('🌙',
                    style: TextStyle(
                        fontSize: 18,
                        color: _amberOrb.withValues(alpha: 0.85))),
              ),
            ),
          ValueListenableBuilder(
            valueListenable: UsageService.instance.snapshot,
            builder: (_, __, ___) => Padding(
              padding: const EdgeInsets.only(right: 16),
              child: Center(
                child: Text(_minutesLabel,
                    style: const TextStyle(color: Colors.white38, fontSize: 12)),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const Spacer(flex: 2),
            Center(child: _buildCentralOrb()),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.only(top: 128),
              child: Center(child: _buildStateLabel()),
            ),
            const Spacer(flex: 1),
            Center(child: _buildHoldButton()),
            const SizedBox(height: 84),
          ],
        ),
      ),
    );
  }

  Widget _buildCentralOrb() {
    final color = _stateColor();
    return AnimatedBuilder(
      animation: Listenable.merge([_pulseController, _waveController]),
      builder: (_, __) => SizedBox(
        width: 220, height: 220,
        child: Stack(
          alignment: Alignment.center,
          children: [
            if (_state == _VoiceState.listening || _state == _VoiceState.speaking)
              ..._buildWaveRings(color),
            if (_state == _VoiceState.idle)
              Transform.scale(
                scale: _pulseAnim.value,
                child: Container(
                  width: 160, height: 160,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: color.withValues(alpha: 0.25), width: 1.5),
                  ),
                ),
              ),
            AnimatedContainer(
              duration: const Duration(milliseconds: 400),
              width:  _state == _VoiceState.listening ? 120 : 100,
              height: _state == _VoiceState.listening ? 120 : 100,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color:  color.withValues(alpha: 0.15),
                border: Border.all(color: color.withValues(alpha: 0.6), width: 2),
                boxShadow: [BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 40, spreadRadius: 8)],
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
      ),
    );
  }

  List<Widget> _buildWaveRings(Color color) => List.generate(3, (i) {
    final scale   = 1.0 + (i * 0.18) + (_waveController.value * 0.12 * (i + 1));
    final opacity = (0.18 - i * 0.05).clamp(0.0, 1.0);
    return Transform.scale(
      scale: scale,
      child: Container(
        width: 100, height: 100,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          border: Border.all(color: color.withValues(alpha: opacity), width: 1.5),
        ),
      ),
    );
  });

  Widget _buildOrbIcon() {
    switch (_state) {
      case _VoiceState.idle:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 52, height: 52, fit: BoxFit.cover, key: const ValueKey('idle')));
      case _VoiceState.listening:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 58, height: 58, fit: BoxFit.cover, key: const ValueKey('listening')));
      case _VoiceState.thinking:
        return SizedBox(
            key: const ValueKey('thinking'), width: 28, height: 28,
            child: CircularProgressIndicator(
                strokeWidth: 2,
                color: _isThreeAm ? _amberOrb : Colors.white70));
      case _VoiceState.speaking:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 52, height: 52, fit: BoxFit.cover, key: const ValueKey('speaking')));
    }
  }

  Widget _buildStateLabel() {
    final threeAm = _isThreeAm;
    String label;
    switch (_state) {
      // In 3am mode idle label is warmer
      case _VoiceState.idle:
        label = threeAm ? 'I\'m here… hold to speak' : 'Hold to speak';
        break;
      case _VoiceState.listening: label = 'Listening…';  break;
      case _VoiceState.thinking:  label = 'Thinking…';   break;
      case _VoiceState.speaking:  label = 'Tap to stop';  break;
    }
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(label, key: ValueKey(label),
          style: TextStyle(
              color: threeAm
                  ? _amberOrb.withValues(alpha: 0.70)
                  : Colors.white38,
              fontSize: 15,
              letterSpacing: 0.5)),
    );
  }

  Widget _buildHoldButton() {
    final isListening = _state == _VoiceState.listening;
    final isSpeaking  = _state == _VoiceState.speaking;
    final threeAm     = _isThreeAm;

    final activeColor = threeAm ? _amberBorder : const Color(0xFF32D0BE);
    final stopColor   = threeAm ? _amberGlow   : const Color(0xFFFF6B6B);

    return GestureDetector(
      onTapDown:   (_) => _onHold(),
      onTapUp:     (_) => _onRelease(),
      onTapCancel: () => _onRelease(),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width:  isListening ? 80 : 72,
        height: isListening ? 80 : 72,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isListening
              ? activeColor.withValues(alpha: 0.2)
              : isSpeaking
                  ? stopColor.withValues(alpha: 0.15)
                  : Colors.white.withValues(alpha: 0.06),
          border: Border.all(
            color: isListening
                ? activeColor.withValues(alpha: 0.8)
                : isSpeaking
                    ? stopColor.withValues(alpha: 0.60)
                    : Colors.white.withValues(alpha: 0.15),
            width: isListening || isSpeaking ? 2 : 1,
          ),
        ),
        child: Icon(
          isListening || isSpeaking ? Icons.stop_rounded : Icons.mic_rounded,
          color: isListening
              ? activeColor
              : isSpeaking
                  ? stopColor
                  : Colors.white.withValues(alpha: 0.6),
          size: 30,
        ),
      ),
    );
  }
}

class _BytesSource extends StreamAudioSource {
  final Uint8List _bytes;
  final String    _contentType;
  _BytesSource(this._bytes, {required String contentType})
      : _contentType = contentType;

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    final s = start ?? 0;
    final e = end   ?? _bytes.length;
    return StreamAudioResponse(
      sourceLength:  _bytes.length,
      contentLength: e - s,
      offset: s,
      stream: Stream.value(_bytes.sublist(s, e)),
      contentType: _contentType,
    );
  }
}
