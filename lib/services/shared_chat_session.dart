// lib/services/shared_chat_session.dart
//
// Single source of truth for conversation history, shared between
// VoiceChatScreen and ChatScreen so both have full context regardless
// of which screen the user switches between.

import 'package:flutter/foundation.dart';
import 'package:mindcore_ai/pages/helpers/chat_persistence.dart';

class SharedChatSession {
  SharedChatSession._();
  static final instance = SharedChatSession._();

  String _conversationId = '';
  final List<Map<String, String>> _history = [];
  bool _loaded = false;

  String get conversationId => _conversationId;

  /// A fresh copy safe to pass directly to ChatStreamService.
  List<Map<String, String>> get historyForAI => List.from(_history);

  bool get isLoaded => _loaded;
  int  get messageCount => _history.length;

  // ── Lifecycle ────────────────────────────────────────────────────────────

  /// Call from initState / _boot of both screens. Idempotent.
  Future<void> ensureLoaded() async {
    if (_loaded) return;
    _conversationId = await ChatPersistence.ensureDefault();
    await _loadHistoryFromDisk();
    _loaded = true;
    if (kDebugMode) {
      print('SharedChatSession: loaded ${_history.length} messages '
            'from conv=$_conversationId');
    }
  }

  /// Switch to a specific conversation (user picks from list).
  Future<void> switchConversation(String id) async {
    if (_conversationId == id && _loaded) return;
    _conversationId = id;
    await _loadHistoryFromDisk();
    _loaded = true;
  }

  /// Reload from disk — call after ChatPersistence.save() if needed.
  Future<void> reloadFromDisk() async => _loadHistoryFromDisk();

  /// Call on logout.
  void invalidate() {
    _history.clear();
    _loaded = false;
    _conversationId = '';
  }

  // ── Message management ───────────────────────────────────────────────────

  void addUser(String text) {
    if (text.trim().isEmpty) return;
    _history.add({'role': 'user', 'content': text.trim()});
  }

  void addAssistant(String text) {
    if (text.trim().isEmpty) return;
    _history.add({'role': 'assistant', 'content': text.trim()});
  }

  // ── Internal ─────────────────────────────────────────────────────────────

  Future<void> _loadHistoryFromDisk() async {
    try {
      final messages = await ChatPersistence.load(_conversationId);
      _history.clear();
      for (final msg in messages) {
        final text = msg.text.trim();
        if (text.isEmpty) continue;
        _history.add({
          'role': msg.isUser ? 'user' : 'assistant',
          'content': text,
        });
      }
    } catch (e) {
      if (kDebugMode) print('SharedChatSession._loadHistoryFromDisk: $e');
    }
  }
}
