// OpenAI-only TTS service for MindCore AI.
// No backend relay. No chunk streaming. just_audio only.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:just_audio/just_audio.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
      if (done) {
        _clearActive();
      }
    });
  }

  static final OpenAiTtsService instance = OpenAiTtsService._internal();

  static const String _endpoint = 'https://api.openai.com/v1/audio/speech';
  static const String _model = 'gpt-4o-mini-tts';
  static const String _defaultVoice = 'nova';
  static const String _defaultFormat = 'wav';

  static String get _apiKey {
    final fromDotenv = dotenv.env['OPENAI_API_KEY']?.trim() ?? '';
    if (fromDotenv.isNotEmpty) return fromDotenv;
    return const String.fromEnvironment('OPENAI_API_KEY', defaultValue: '').trim();
  }

  final AudioPlayer _player = AudioPlayer();
  final Map<TtsSurface, bool> _surfaceEnabled = {
    for (final s in TtsSurface.values) s: s.defaultEnabled,
  };

  bool _enabled = true;
  bool _moodAdaptive = true;
  double _baseSpeed = 0.96;
  String _voice = _defaultVoice;
  int _requestToken = 0;
  bool _isSpeaking = false;
  String? _activeMessageId;
  TtsSurface? _activeSurface;
  final Map<TtsSurface, _TtsMemory> _lastBySurface = {};
  final Map<String, Uint8List> _audioCache = {};

  Future<void> init() async {
    await loadSettings();
  }

  bool get enabled => _enabled;
  bool get moodAdaptive => _moodAdaptive;
  double get baseSpeed => _baseSpeed;
  String get voice => _voice;
  bool get isSpeakingNow => _isSpeaking;
  String? get activeMessageId => _activeMessageId;
  TtsSurface? get activeSurface => _activeSurface;

  bool isEnabled() => _enabled;

  bool isSpeakingMessage(String? messageId) {
    return _isSpeaking && messageId != null && _activeMessageId == messageId;
  }

  bool isSurfaceEnabled(TtsSurface surface) {
    return _surfaceEnabled[surface] ?? surface.defaultEnabled;
  }

  bool hasReplay(TtsSurface surface) {
    final memory = _lastBySurface[surface];
    return memory != null && memory.text.trim().isNotEmpty;
  }

  Future<bool> replayLast(TtsSurface surface, {bool force = true}) async {
    final memory = _lastBySurface[surface];
    if (memory == null || memory.text.trim().isEmpty) return false;
    return speak(
      memory.text,
      moodLabel: memory.moodLabel,
      messageId: memory.messageId,
      surface: surface,
      force: force,
    );
  }

  Future<bool> getEnabled() async {
    await loadSettings();
    return _enabled;
  }

  Future<void> setEnabled(bool value) async {
    _enabled = value;
    await _saveSettings();
    if (!value) {
      await stop();
    }
  }

  Future<bool> getMoodAdaptive() async {
    await loadSettings();
    return _moodAdaptive;
  }

  Future<void> setMoodAdaptive(bool value) async {
    _moodAdaptive = value;
    await _saveSettings();
  }

  Future<void> setBaseSpeed(double value) async {
    _baseSpeed = value.clamp(0.84, 1.04);
    await _saveSettings();
  }

  Future<String> getVoice() async {
    await loadSettings();
    return _voice;
  }

  Future<void> setVoice(String value) async {
    _voice = value.trim().isEmpty ? _defaultVoice : value.trim();
    await _saveSettings();
  }

  Future<bool> getSurfaceEnabled(TtsSurface surface) async {
    await loadSettings();
    return isSurfaceEnabled(surface);
  }

  Future<void> setSurfaceEnabled(TtsSurface surface, bool value) async {
    _surfaceEnabled[surface] = value;
    await _saveSettings();
    if (!value && _activeSurface == surface) {
      await stop();
    }
  }

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _enabled = prefs.getBool('tts_enabled') ?? true;
    _moodAdaptive = prefs.getBool('tts_mood_adaptive') ?? true;
    _baseSpeed = prefs.getDouble('tts_speed') ?? 0.96;
    _voice = prefs.getString('tts_voice') ?? _defaultVoice;
    for (final surface in TtsSurface.values) {
      _surfaceEnabled[surface] =
          prefs.getBool(surface.prefsKey) ?? surface.defaultEnabled;
    }
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('tts_enabled', _enabled);
    await prefs.setBool('tts_mood_adaptive', _moodAdaptive);
    await prefs.setDouble('tts_speed', _baseSpeed);
    await prefs.setString('tts_voice', _voice);
    for (final entry in _surfaceEnabled.entries) {
      await prefs.setBool(entry.key.prefsKey, entry.value);
    }
  }

  Future<bool> speak(
    String text, {
    String moodLabel = 'neutral',
    String? messageId,
    TtsSurface surface = TtsSurface.chat,
    bool force = false,
  }) async {
    if (!_enabled) return false;
    if (!force && !isSurfaceEnabled(surface)) return false;

    final apiKey = _apiKey;
    if (apiKey.isEmpty) return false;

    final cleaned = _cleanText(text);
    if (cleaned.isEmpty) return false;

    final resolvedMessageId = messageId ?? '${surface.name}_${cleaned.hashCode}';
    _lastBySurface[surface] = _TtsMemory(
      text: cleaned,
      moodLabel: moodLabel,
      messageId: resolvedMessageId,
    );

    if (isSpeakingMessage(resolvedMessageId)) {
      return true;
    }

    final token = ++_requestToken;
    await _stopPlaybackOnly();
    if (token != _requestToken) return false;

    final mood = _mapMood(moodLabel);
    final speed = _speedFor(surface, mood);
    final voice = _voiceFor(surface, mood);

    final cacheKey = '$voice|${speed.toStringAsFixed(2)}|$cleaned';
    final bytes = _audioCache[cacheKey] ??
        await _synthesize(
          text: cleaned,
          voice: voice,
          speed: speed,
          apiKey: apiKey,
        );

    if (token != _requestToken) return false;
    if (bytes == null || bytes.isEmpty) {
      _clearActive();
      return false;
    }

    if (bytes != null && bytes.isNotEmpty) {
      _audioCache[cacheKey] = bytes;
      if (_audioCache.length > 12) {
        _audioCache.remove(_audioCache.keys.first);
      }
    }

    _activeMessageId = resolvedMessageId;
    _activeSurface = surface;
    _isSpeaking = true;
    notifyListeners();

    try {
      await _player.setAudioSource(_BytesAudioSource(bytes, contentType: _contentTypeForFormat(_defaultFormat)));
      if (token != _requestToken) {
        await _stopPlaybackOnly();
        _clearActive();
        return false;
      }
      await _player.play();
      return true;
    } catch (_) {
      if (token == _requestToken) {
        _clearActive();
      }
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
        '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    final key = 'tts_once_day_${surface.name}_$uniqueKey';
    if (prefs.getString(key) == ymd) return false;

    final ok = await speak(
      text,
      moodLabel: moodLabel,
      messageId: messageId ?? '${surface.name}_$uniqueKey',
      surface: surface,
    );
    if (ok) {
      await prefs.setString(key, ymd);
    }
    return ok;
  }

  Future<void> stop() async {
    _requestToken++;
    await _stopPlaybackOnly();
    _clearActive();
  }

  Future<void> stopIfSurface(TtsSurface surface) async {
    if (_activeSurface == surface) {
      await stop();
    }
  }

  Future<void> _stopPlaybackOnly() async {
    try {
      await _player.stop();
    } catch (_) {}
  }

  void _clearActive() {
    final changed = _activeMessageId != null || _activeSurface != null || _isSpeaking;
    _activeMessageId = null;
    _activeSurface = null;
    _isSpeaking = false;
    if (changed) {
      notifyListeners();
    }
  }

  Future<Uint8List?> _synthesize({
    required String text,
    required String voice,
    required double speed,
    required String apiKey,
  }) async {
    try {
      final res = await http.post(
        Uri.parse(_endpoint),
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'model': _model,
          'voice': voice,
          'input': text,
          'format': _defaultFormat,
          'speed': speed,
        }),
      );
      if (res.statusCode != 200) return null;
      return Uint8List.fromList(res.bodyBytes);
    } catch (_) {
      return null;
    }
  }

  String _cleanText(String text) {
    var cleaned = text.replaceAll('\r', ' ').replaceAll('\n', ' ');
    cleaned = cleaned.replaceAll(RegExp(r'\s+'), ' ');
    cleaned = cleaned.replaceAll('•', '');
    cleaned = cleaned.replaceAllMapped(
      RegExp(r'([a-zA-Z])\s*-\s*([a-zA-Z])'),
      (m) => '${m.group(1)} ${m.group(2)}',
    );
    return cleaned.trim();
  }



  String _contentTypeForFormat(String format) {
    switch (format) {
      case 'wav':
        return 'audio/wav';
      case 'aac':
        return 'audio/aac';
      case 'flac':
        return 'audio/flac';
      case 'opus':
        return 'audio/opus';
      case 'pcm':
        return 'audio/pcm';
      case 'mp3':
      default:
        return 'audio/mpeg';
    }
  }

  TtsMood _mapMood(String label) {
    final value = label.toLowerCase();
    if (value.contains('anx') || value.contains('panic') || value.contains('overwhelm')) {
      return TtsMood.anxious;
    }
    if (value.contains('sad') || value.contains('low') || value.contains('down')) {
      return TtsMood.low;
    }
    if (value.contains('calm') || value.contains('good') || value.contains('relax')) {
      return TtsMood.calm;
    }
    return TtsMood.neutral;
  }

  String _voiceFor(TtsSurface surface, TtsMood mood) {
    if (surface == TtsSurface.recommendation ||
        surface == TtsSurface.dailyMotivation ||
        surface == TtsSurface.journal ||
        surface == TtsSurface.reflection ||
        mood == TtsMood.anxious ||
        mood == TtsMood.low ||
        mood == TtsMood.calm) {
      return 'nova';
    }
    return _voice.trim().isEmpty ? _defaultVoice : _voice.trim();
  }

  double _speedFor(TtsSurface surface, TtsMood mood) {
    var speed = _baseSpeed.clamp(0.84, 1.04);

    switch (surface) {
      case TtsSurface.recommendation:
      case TtsSurface.dailyMotivation:
        speed -= 0.03;
        break;
      case TtsSurface.journal:
      case TtsSurface.reflection:
      case TtsSurface.breathe:
        speed -= 0.02;
        break;
      case TtsSurface.chat:
        break;
    }

    if (_moodAdaptive) {
      switch (mood) {
        case TtsMood.anxious:
        case TtsMood.low:
          speed -= 0.02;
          break;
        case TtsMood.calm:
        case TtsMood.neutral:
          break;
      }
    }

    return speed.clamp(0.84, 1.04);
  }
}

class _BytesAudioSource extends StreamAudioSource {
  _BytesAudioSource(this.bytes, {required this.contentType});

  final Uint8List bytes;
  final String contentType;

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end ??= bytes.length;
    return StreamAudioResponse(
      sourceLength: bytes.length,
      contentLength: end - start,
      offset: start,
      stream: Stream.value(bytes.sublist(start, end)),
      contentType: contentType,
    );
  }
}

class _TtsMemory {
  final String text;
  final String moodLabel;
  final String messageId;

  const _TtsMemory({
    required this.text,
    required this.moodLabel,
    required this.messageId,
  });
}
