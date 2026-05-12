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
  List<Map<String, String>> get historyForAI => List.from(_history);
  bool get isLoaded => _loaded;
  int  get messageCount => _history.length;

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

  Future<void> switchConversation(String id) async {
    if (_conversationId == id && _loaded) return;
    _conversationId = id;
    await _loadHistoryFromDisk();
    _loaded = true;
  }

  Future<void> reloadFromDisk() async => _loadHistoryFromDisk();

  void invalidate() {
    _history.clear();
    _loaded = false;
    _conversationId = '';
  }

  void addUser(String text) {
    if (text.trim().isEmpty) return;
    _history.add({'role': 'user', 'content': text.trim()});
  }

  void addAssistant(String text) {
    if (text.trim().isEmpty) return;
    _history.add({'role': 'assistant', 'content': text.trim()});
  }

  Future<void> _loadHistoryFromDisk() async {
    try {
      final messages = await ChatPersistence.load(_conversationId);
      _history.clear();
      for (final msg in messages) {
        final text = msg.text.trim();
        if (text.isEmpty) continue;
        // ChatMessage uses role: 'user' | 'assistant' (no isUser getter)
        _history.add({
          'role': msg.role == 'user' ? 'user' : 'assistant',
          'content': text,
        });
      }
    } catch (e) {
      if (kDebugMode) print('SharedChatSession._loadHistoryFromDisk: $e');
    }
  }
}
