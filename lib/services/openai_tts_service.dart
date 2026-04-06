// OpenAI chat + Fish Audio TTS service for MindCore AI.
// All public API is identical — only the underlying synthesis call changed.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/env/env.dart';

enum TtsMood { calm, anxious, low, neutral }

enum TtsSurface {
  chat,
  recommendation,
  dailyMotivation,
  journal,
  reflection,
  breathe,
}

extension TtsSurfaceX on TtsSurface {
  String get prefsKey {
    switch (this) {
      case TtsSurface.chat:
        return 'tts_surface_chat';
      case TtsSurface.recommendation:
        return 'tts_surface_recommendation';
      case TtsSurface.dailyMotivation:
        return 'tts_surface_daily_motivation';
      case TtsSurface.journal:
        return 'tts_surface_journal';
      case TtsSurface.reflection:
        return 'tts_surface_reflection';
      case TtsSurface.breathe:
        return 'tts_surface_breathe';
    }
  }

  String get label {
    switch (this) {
      case TtsSurface.chat:
        return 'Chat replies';
      case TtsSurface.recommendation:
        return 'Recommendations';
      case TtsSurface.dailyMotivation:
        return 'Daily motivation';
      case TtsSurface.journal:
        return 'Journal entries';
      case TtsSurface.reflection:
        return 'AI reflections';
      case TtsSurface.breathe:
        return 'Breathing cues';
    }
  }

  bool get defaultEnabled {
    switch (this) {
      case TtsSurface.chat:
      case TtsSurface.recommendation:
      case TtsSurface.dailyMotivation:
      case TtsSurface.breathe:
        return true;
      case TtsSurface.journal:
      case TtsSurface.reflection:
        return false;
    }
  }
}

class OpenAiTtsService extends ChangeNotifier {
  OpenAiTtsService._internal() {
    _player.playerStateStream.listen((state) {
      final done = state.processingState == ProcessingState.completed ||
          state.processingState == ProcessingState.idle ||
          !state.playing;
      if (done) _clearActive();
    });
  }

  static final OpenAiTtsService instance = OpenAiTtsService._internal();

  // ── Fish Audio constants ───────────────────────────────────────────
  static const String _fishEndpoint = 'https://api.fish.audio/v1/tts';
  static const String _fishFormat   = 'mp3';
  static const String _fishLatency  = 'normal';

  static String get _fishApiKey {
    // 1. Compile-time dart-define
    const fromEnv = Env.fishAudioKey;
    if (fromEnv.isNotEmpty) return fromEnv;
    // 2. Runtime .env (flutter_dotenv)
    final fromDotenv = dotenv.env['FISH_AUDIO_API_KEY']?.trim() ?? '';
    return fromDotenv;
  }

  static String get _fishVoiceId {
    const fromEnv = Env.fishAudioVoiceId;
    if (fromEnv.isNotEmpty) return fromEnv;
    return dotenv.env['FISH_AUDIO_VOICE_ID']?.trim() ??
        '0b74ead073f2474a904f69033535b98e';
  }

  // ── Player & state ─────────────────────────────────────────────────
  final AudioPlayer _player = AudioPlayer();
  final Map<TtsSurface, bool> _surfaceEnabled = {
    for (final s in TtsSurface.values) s: s.defaultEnabled,
  };

  bool   _enabled     = true;
  bool   _moodAdaptive = true;
  double _baseSpeed    = 0.96; // kept for settings compatibility
  int    _requestToken = 0;
  bool   _isSpeaking   = false;
  String? _activeMessageId;
  TtsSurface? _activeSurface;
  final Map<TtsSurface, _TtsMemory> _lastBySurface = {};
  final Map<String, Uint8List>      _audioCache    = {};

  Future<void> init() async => loadSettings();

  // ── Public getters ──────────────────────────────────────────────────
  bool        get enabled         => _enabled;
  bool        get moodAdaptive    => _moodAdaptive;
  double      get baseSpeed       => _baseSpeed;
  bool        get isSpeakingNow   => _isSpeaking;
  String?     get activeMessageId => _activeMessageId;
  TtsSurface? get activeSurface   => _activeSurface;

  bool isEnabled() => _enabled;

  bool isSpeakingMessage(String? messageId) =>
      _isSpeaking && messageId != null && _activeMessageId == messageId;

  bool isSurfaceEnabled(TtsSurface surface) =>
      _surfaceEnabled[surface] ?? surface.defaultEnabled;

  bool hasReplay(TtsSurface surface) {
    final m = _lastBySurface[surface];
    return m != null && m.text.trim().isNotEmpty;
  }

  Future<bool> replayLast(TtsSurface surface, {bool force = true}) async {
    final m = _lastBySurface[surface];
    if (m == null || m.text.trim().isEmpty) return false;
    return speak(m.text,
        moodLabel: m.moodLabel, messageId: m.messageId, surface: surface, force: force);
  }

  // ── Settings ─────────────────────────────────────────────────────────
  Future<bool>   getEnabled()     async { await loadSettings(); return _enabled; }
  Future<bool>   getMoodAdaptive() async { await loadSettings(); return _moodAdaptive; }
  Future<String> getVoice()       async { await loadSettings(); return _fishVoiceId; }

  Future<void> setEnabled(bool v)       async { _enabled = v; await _saveSettings(); if (!v) await stop(); }
  Future<void> setMoodAdaptive(bool v)  async { _moodAdaptive = v; await _saveSettings(); }
  Future<void> setBaseSpeed(double v)   async { _baseSpeed = v.clamp(0.84, 1.04); await _saveSettings(); }
  Future<void> setVoice(String v)       async { await _saveSettings(); } // voice is set via env

  Future<bool> getSurfaceEnabled(TtsSurface s) async { await loadSettings(); return isSurfaceEnabled(s); }
  Future<void> setSurfaceEnabled(TtsSurface s, bool v) async {
    _surfaceEnabled[s] = v;
    await _saveSettings();
    if (!v && _activeSurface == s) await stop();
  }

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _enabled      = prefs.getBool('tts_enabled') ?? true;
    _moodAdaptive = prefs.getBool('tts_mood_adaptive') ?? true;
    _baseSpeed    = prefs.getDouble('tts_speed') ?? 0.96;
    for (final s in TtsSurface.values) {
      _surfaceEnabled[s] = prefs.getBool(s.prefsKey) ?? s.defaultEnabled;
    }
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('tts_enabled', _enabled);
    await prefs.setBool('tts_mood_adaptive', _moodAdaptive);
    await prefs.setDouble('tts_speed', _baseSpeed);
    for (final e in _surfaceEnabled.entries) {
      await prefs.setBool(e.key.prefsKey, e.value);
    }
  }

  // ── Core speak ──────────────────────────────────────────────────────
  Future<bool> speak(
    String text, {
    String moodLabel = 'neutral',
    String? messageId,
    TtsSurface surface = TtsSurface.chat,
    bool force = false,
  }) async {
    if (!_enabled) return false;
    if (!force && !isSurfaceEnabled(surface)) return false;

    final apiKey = _fishApiKey;
    if (apiKey.isEmpty) {
      debugPrint('[TTS] FISH_AUDIO_API_KEY is not set.');
      return false;
    }

    final cleaned = _cleanText(text);
    if (cleaned.isEmpty) return false;

    final resolvedId = messageId ?? '${surface.name}_${cleaned.hashCode}';
    _lastBySurface[surface] =
        _TtsMemory(text: cleaned, moodLabel: moodLabel, messageId: resolvedId);

    if (isSpeakingMessage(resolvedId)) return true;

    final token = ++_requestToken;
    await _stopPlaybackOnly();
    if (token != _requestToken) return false;

    // Cache key — voice ID + text (Fish Audio has no speed param)
    final cacheKey = '${_fishVoiceId}|$cleaned';
    final bytes = _audioCache[cacheKey] ??
        await _synthesize(text: cleaned, apiKey: apiKey);

    if (token != _requestToken) return false;
    if (bytes == null || bytes.isEmpty) {
      _clearActive();
      return false;
    }

    _audioCache[cacheKey] = bytes;
    if (_audioCache.length > 12) _audioCache.remove(_audioCache.keys.first);

    _activeMessageId = resolvedId;
    _activeSurface   = surface;
    _isSpeaking      = true;
    notifyListeners();

    try {
      await _player.setAudioSource(
          _BytesAudioSource(bytes, contentType: 'audio/mpeg'));
      if (token != _requestToken) {
        await _stopPlaybackOnly();
        _clearActive();
        return false;
      }
      await _player.play();
      return true;
    } catch (e) {
      debugPrint('[TTS] Playback error: $e');
      if (token == _requestToken) _clearActive();
      return false;
    }
  }

  Future<bool> maybeSpeakOncePerDay({
    required String uniqueKey,
    required String text,
    required TtsSurface surface,
    String moodLabel = 'neutral',
    String? messageId,
  }) async {
    if (!_enabled || !isSurfaceEnabled(surface)) return false;
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    final ymd =
        '${now.year.toString().padLeft(4, '0')}-'
        '${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';
    final key = 'tts_once_day_${surface.name}_$uniqueKey';
    if (prefs.getString(key) == ymd) return false;
    final ok = await speak(text,
        moodLabel: moodLabel,
        messageId: messageId ?? '${surface.name}_$uniqueKey',
        surface: surface);
    if (ok) await prefs.setString(key, ymd);
    return ok;
  }

  Future<void> stop() async {
    _requestToken++;
    await _stopPlaybackOnly();
    _clearActive();
  }

  Future<void> stopIfSurface(TtsSurface surface) async {
    if (_activeSurface == surface) await stop();
  }

  Future<void> flushVoiceBuffer() async {} // kept for call-site compatibility

  // ── Fish Audio synthesis ──────────────────────────────────────────────
  Future<Uint8List?> _synthesize({
    required String text,
    required String apiKey,
  }) async {
    try {
      final res = await http
          .post(
            Uri.parse(_fishEndpoint),
            headers: {
              'Authorization': 'Bearer $apiKey',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'text':         text,
              'reference_id': _fishVoiceId,
              'format':       _fishFormat,
              'latency':      _fishLatency,
            }),
          )
          .timeout(const Duration(seconds: 20));

      if (res.statusCode != 200) {
        debugPrint('[TTS] Fish Audio error ${res.statusCode}: ${res.body}');
        return null;
      }
      return Uint8List.fromList(res.bodyBytes);
    } catch (e) {
      debugPrint('[TTS] Fish Audio exception: $e');
      return null;
    }
  }

  // ── Internals ──────────────────────────────────────────────────────────
  Future<void> _stopPlaybackOnly() async {
    try { await _player.stop(); } catch (_) {}
  }

  void _clearActive() {
    final changed = _activeMessageId != null ||
        _activeSurface != null ||
        _isSpeaking;
    _activeMessageId = null;
    _activeSurface   = null;
    _isSpeaking      = false;
    if (changed) notifyListeners();
  }

  String _cleanText(String text) {
    var c = text.replaceAll('\r', ' ').replaceAll('\n', ' ');
    c = c.replaceAll(RegExp(r'\s+'), ' ');
    c = c.replaceAll('•', '');
    c = c.replaceAllMapped(
      RegExp(r'([a-zA-Z])\s*-\s*([a-zA-Z])'),
      (m) => '${m.group(1)} ${m.group(2)}',
    );
    return c.trim();
  }
}

// ── Audio source helpers ─────────────────────────────────────────────────────

class _BytesAudioSource extends StreamAudioSource {
  final Uint8List bytes;
  final String contentType;
  _BytesAudioSource(this.bytes, {required this.contentType});

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end   ??= bytes.length;
    return StreamAudioResponse(
      sourceLength:  bytes.length,
      contentLength: end - start,
      offset:        start,
      stream:        Stream.value(bytes.sublist(start, end)),
      contentType:   contentType,
    );
  }
}

class _TtsMemory {
  final String text;
  final String moodLabel;
  final String messageId;
  const _TtsMemory(
      {required this.text,
      required this.moodLabel,
      required this.messageId});
}
