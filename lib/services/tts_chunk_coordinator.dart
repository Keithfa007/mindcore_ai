import 'dart:async';
import 'dart:collection';

typedef TtsChunkPlayer = Future<void> Function(String chunk, int chunkIndex, String? nextChunk);

class TtsChunkCoordinator {
  String? _sessionId;
  int _lastBoundary = 0;
  bool _cancelled = false;
  int _chunkIndex = 0;

  final Queue<String> _queue = Queue<String>();
  bool _draining = false;

  static const int _minChunk = 120;
  static const int _idealChunk = 180;
  static const int _maxChunk = 240;
  static const int _finalMinChunk = 40;

  void startSession(String sessionId) {
    if (_sessionId == sessionId) return;
    _sessionId = sessionId;
    _lastBoundary = 0;
    _cancelled = false;
    _chunkIndex = 0;
    _queue.clear();
    _draining = false;
  }

  void cancel() {
    _cancelled = true;
    _queue.clear();
  }

  void ingest({
    required String sessionId,
    required String fullText,
    required TtsChunkPlayer player,
  }) {
    if (_sessionId != sessionId) {
      startSession(sessionId);
    }
    if (_cancelled) return;
    if (fullText.length < _lastBoundary) {
      _lastBoundary = 0;
    }

    while (!_cancelled && _lastBoundary < fullText.length) {
      final remaining = fullText.substring(_lastBoundary);
      final nextLength = _extractChunkLength(remaining, isFinal: false);
      if (nextLength == null) break;

      final segment = remaining.substring(0, nextLength).trim();
      _lastBoundary += nextLength;
      _enqueueSegment(segment, player);
    }
  }

  Future<void> finish({
    required String sessionId,
    required String fullText,
    required TtsChunkPlayer player,
  }) async {
    if (_sessionId != sessionId) {
      startSession(sessionId);
    }
    if (_cancelled) return;

    while (!_cancelled && _lastBoundary < fullText.length) {
      final remaining = fullText.substring(_lastBoundary);
      final nextLength = _extractChunkLength(remaining, isFinal: true) ?? remaining.length;
      final segment = remaining.substring(0, nextLength).trim();
      _lastBoundary += nextLength;
      _enqueueSegment(segment, player);
    }
    await _drain(player);
  }

  void _enqueueSegment(String segment, TtsChunkPlayer player) {
    final normalized = segment.replaceAll(RegExp(r'\s+'), ' ').replaceAll('•', '').trim();
    if (normalized.isEmpty) return;
    if (normalized.length < _finalMinChunk && _queue.isNotEmpty) return;
    _queue.add(normalized);
    unawaited(_drain(player));
  }

  int? _extractChunkLength(String text, {required bool isFinal}) {
    if (text.trim().isEmpty) return null;

    final effectiveMax = text.length < _maxChunk ? text.length : _maxChunk;
    final window = text.substring(0, effectiveMax);

    int? strong = _findLastBoundary(window, ['.', '!', '?', ';', ':']);
    if (strong != null && (strong >= _minChunk || (isFinal && strong >= _finalMinChunk))) {
      return strong;
    }

    int? soft = _findLastBoundary(window, [',']);
    if (soft != null && soft >= _idealChunk) {
      return soft;
    }

    int? space = window.lastIndexOf(' ');
    if (space >= _idealChunk) {
      return space + 1;
    }

    if (isFinal && text.length >= _finalMinChunk) {
      return text.length;
    }

    if (text.length >= _maxChunk) {
      return effectiveMax;
    }

    return null;
  }

  int? _findLastBoundary(String text, List<String> marks) {
    int boundary = -1;
    for (int i = 0; i < text.length; i++) {
      final char = text[i];
      if (!marks.contains(char)) continue;
      final nextIndex = i + 1;
      final isBoundary = nextIndex >= text.length || text[nextIndex] == ' ' || text[nextIndex] == '\n';
      if (isBoundary) {
        boundary = nextIndex;
      }
    }
    return boundary >= 0 ? boundary : null;
  }

  Future<void> _drain(TtsChunkPlayer player) async {
    if (_draining) return;
    _draining = true;
    try {
      while (_queue.isNotEmpty && !_cancelled) {
        final next = _queue.removeFirst();
        final idx = _chunkIndex++;
        final upcoming = _queue.isNotEmpty ? _queue.first : null;
        await player(next, idx, upcoming);
      }
    } finally {
      _draining = false;
    }
  }
}
