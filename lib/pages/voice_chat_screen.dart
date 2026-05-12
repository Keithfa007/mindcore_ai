// lib/pages/voice_chat_screen.dart
import 'dart:async';
import 'dart:collection';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:uuid/uuid.dart';

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

  _VoiceState _state          = _VoiceState.idle;
  bool        _sttReady       = false;
  String      _moodLabel      = 'calm';
  int         _voiceMessageCount = 0;

  // ── Sentence-streaming TTS pipeline ──────────────────────────────────────
  final TtsChunkCoordinator        _coordinator    = TtsChunkCoordinator();
  final AudioPlayer                _chunkPlayer    = AudioPlayer();
  final Queue<Future<_TtsSource?>> _synthesisQueue = Queue();
  bool         _chunkPlaying = false;
  bool         _cancelled    = false;
  http.Client? _activeClient;

  // ── Animations ───────────────────────────────────────────────────────────
  late AnimationController _pulseController;
  late AnimationController _waveController;
  late Animation<double>   _pulseAnim;
  Timer? _voiceTimer;

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
    // Load shared history so voice sees chat messages and vice versa
    unawaited(SharedChatSession.instance.ensureLoaded());
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _waveController.dispose();
    _voiceTimer?.cancel();
    _coordinator.cancel();
    _chunkPlayer.dispose();
    _activeClient?.close();
    UsageService.instance.flushVoiceBuffer();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  // ── Pre-warm ───────────────────────────────────────────────────────────

  Future<void> _preWarm() async {
    try {
      await LiveVoicePreferences.instance.load();
      await _chunkPlayer.setVolume(1.0);
      final key = Env.fishAudioKey;
      if (key.isEmpty) return;
      final req = http.Request(
          'POST', Uri.parse('https://api.fish.audio/v1/tts'));
      req.headers['Authorization'] = 'Bearer $key';
      req.headers['Content-Type']  = 'application/json';
      req.body = jsonEncode({
        'text': 'hi',
        'reference_id': LiveVoicePreferences.instance.activeVoiceId,
        'format': 'mp3',
        'latency': 'balanced',
      });
      final client = http.Client();
      try {
        final res = await client
            .send(req)
            .timeout(const Duration(seconds: 8));
        await res.stream.drain<void>();
      } finally {
        client.close();
      }
    } catch (_) {}
  }

  // ── Streaming TTS synthesis ────────────────────────────────────────────
  //
  // client.send() returns as soon as HTTP headers arrive (~100ms).
  // just_audio then streams the MP3 bytes from Fish Audio directly,
  // so playback starts while the audio is still being synthesised.
  // Old http.post() waited for the full body (~1-2s) first.

  Future<_TtsSource?> _synthesise(String text) async {
    try {
      final key     = Env.fishAudioKey;
      final voiceId = LiveVoicePreferences.instance.activeVoiceId;
      if (key.isEmpty || text.trim().isEmpty) return null;

      final req = http.Request(
          'POST', Uri.parse('https://api.fish.audio/v1/tts'));
      req.headers['Authorization'] = 'Bearer $key';
      req.headers['Content-Type']  = 'application/json';
      req.body = jsonEncode({
        'text': text.trim(),
        'reference_id': voiceId,
        'format': 'mp3',
        'latency': 'balanced',
      });

      _activeClient?.close();
      final client = http.Client();
      _activeClient = client;

      final response = await client
          .send(req)
          .timeout(const Duration(seconds: 12));

      if (response.statusCode != 200) {
        client.close();
        _activeClient = null;
        return null;
      }

      return _TtsSource(
        stream: response.stream.map((b) => Uint8List.fromList(b)),
        contentLength: response.contentLength,
        client: client,
      );
    } catch (_) {
      _activeClient?.close();
      _activeClient = null;
      return null;
    }
  }

  // ── Chunk pipeline ──────────────────────────────────────────────────────────

  void _enqueueChunk(String text) {
    if (_cancelled) return;
    // Flip to speaking immediately on first sentence — no visible pause
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
        final source = await _synthesisQueue.removeFirst();
        if (source == null || _cancelled || !mounted) {
          source?.client.close();
          continue;
        }
        try {
          await _chunkPlayer.setAudioSource(
            _StreamingAudioSource(source.stream, source.contentLength),
          );
          final completer = Completer<void>();
          final sub = _chunkPlayer.playerStateStream.listen((s) {
            if (!completer.isCompleted) {
              final done =
                  s.processingState == ProcessingState.completed ||
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
        source.client.close();
      }
    } finally {
      _chunkPlaying = false;
      if (mounted && !_cancelled) {
        setState(() => _state = _VoiceState.idle);
      }
    }
  }

  void _cancelAudio() {
    _cancelled = true;
    _coordinator.cancel();
    _activeClient?.close();
    _activeClient = null;
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
    final ok = await _stt.initialize(
        onError: (e) => debugPrint('STT error: $e'));
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
      listenOptions: SpeechListenOptions(
        listenMode: ListenMode.dictation,
        cancelOnError: false,
        // Default pauseFor was ~3s which cut the user off mid-thought.
        // 8s gives enough time to pause and continue naturally.
        pauseFor: const Duration(seconds: 8),
        listenFor: const Duration(minutes: 3),
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
    // Write to shared session so chat screen sees this voice message
    SharedChatSession.instance.addUser(userText);

    _cancelled = false;
    _synthesisQueue.clear();
    _chunkPlaying = false;

    final sessionId   = _uuid.v4();
    _coordinator.startSession(sessionId);
    final accumulated = StringBuffer();

    try {
      // Pass full shared history so AI has context of both chat + voice
      final history = SharedChatSession.instance.historyForAI;
      // Remove current user message — it’s passed separately as userInput
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

      // Write AI reply to shared session so chat screen sees it
      SharedChatSession.instance.addAssistant(result.reply);

      _voiceMessageCount++;
      if (_voiceMessageCount % 5 == 0) {
        unawaited(UserMemoryService.saveMemory(
          SharedChatSession.instance.historyForAI,
        ));
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

  // ── UI ────────────────────────────────────────────────────────────────────

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
      builder: (_, __) {
        return SizedBox(
          width: 220, height: 220,
          child: Stack(
            alignment: Alignment.center,
            children: [
              if (_state == _VoiceState.listening ||
                  _state == _VoiceState.speaking)
                ..._buildWaveRings(color),
              if (_state == _VoiceState.idle)
                Transform.scale(
                  scale: _pulseAnim.value,
                  child: Container(
                    width: 160, height: 160,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                          color: color.withValues(alpha: 0.25), width: 1.5),
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
                  boxShadow: [
                    BoxShadow(
                        color: color.withValues(alpha: 0.3),
                        blurRadius: 40, spreadRadius: 8)
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
      final scale = 1.0 + (i * 0.18) + (_waveController.value * 0.12 * (i + 1));
      final opacity = (0.18 - i * 0.05).clamp(0.0, 1.0);
      return Transform.scale(
        scale: scale,
        child: Container(
          width: 100, height: 100,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
                color: color.withValues(alpha: opacity), width: 1.5),
          ),
        ),
      );
    });
  }

  Widget _buildOrbIcon() {
    switch (_state) {
      case _VoiceState.idle:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 52, height: 52, fit: BoxFit.cover, key: const ValueKey('idle')));
      case _VoiceState.listening:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 58, height: 58, fit: BoxFit.cover, key: const ValueKey('listening')));
      case _VoiceState.thinking:
        return const SizedBox(
            key: ValueKey('thinking'), width: 28, height: 28,
            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white70));
      case _VoiceState.speaking:
        return ClipOval(child: Image.asset('assets/images/logo512.png',
            width: 52, height: 52, fit: BoxFit.cover, key: const ValueKey('speaking')));
    }
  }

  Color _stateColor() {
    switch (_state) {
      case _VoiceState.idle:      return const Color(0xFF4D7CFF);
      case _VoiceState.listening: return const Color(0xFF32D0BE);
      case _VoiceState.thinking:  return const Color(0xFF9B7FFF);
      case _VoiceState.speaking:  return const Color(0xFF4D7CFF);
    }
  }

  Widget _buildStateLabel() {
    String label;
    switch (_state) {
      case _VoiceState.idle:      label = 'Hold to speak'; break;
      case _VoiceState.listening: label = 'Listening…';    break;
      case _VoiceState.thinking:  label = 'Thinking…';     break;
      case _VoiceState.speaking:  label = 'Tap to stop';   break;
    }
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 300),
      child: Text(label,
          key: ValueKey(label),
          style: const TextStyle(
              color: Colors.white38, fontSize: 15, letterSpacing: 0.5)),
    );
  }

  Widget _buildHoldButton() {
    final isListening = _state == _VoiceState.listening;
    final isSpeaking  = _state == _VoiceState.speaking;
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
              ? const Color(0xFF32D0BE).withValues(alpha: 0.2)
              : isSpeaking
                  ? const Color(0xFFFF6B6B).withValues(alpha: 0.15)
                  : Colors.white.withValues(alpha: 0.06),
          border: Border.all(
            color: isListening
                ? const Color(0xFF32D0BE).withValues(alpha: 0.8)
                : isSpeaking
                    ? const Color(0xFFFF6B6B).withValues(alpha: 0.60)
                    : Colors.white.withValues(alpha: 0.15),
            width: isListening || isSpeaking ? 2 : 1,
          ),
        ),
        child: Icon(
          isListening || isSpeaking ? Icons.stop_rounded : Icons.mic_rounded,
          color: isListening
              ? const Color(0xFF32D0BE)
              : isSpeaking
                  ? const Color(0xFFFF6B6B)
                  : Colors.white.withValues(alpha: 0.6),
          size: 30,
        ),
      ),
    );
  }
}

// ── TTS source ────────────────────────────────────────────────────────────────

class _TtsSource {
  final Stream<Uint8List> stream;
  final int?        contentLength;
  final http.Client client;
  const _TtsSource({
    required this.stream,
    required this.client,
    this.contentLength,
  });
}

// ── Streaming audio source ─────────────────────────────────────────────────────

class _StreamingAudioSource extends StreamAudioSource {
  final Stream<Uint8List> _stream;
  final int?              _contentLength;
  _StreamingAudioSource(this._stream, this._contentLength);

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    return StreamAudioResponse(
      sourceLength:  _contentLength,
      contentLength: _contentLength,
      offset: 0,
      stream: _stream,
      contentType: 'audio/mpeg',
    );
  }
}
