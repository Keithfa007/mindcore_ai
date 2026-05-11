// lib/pages/helpers/chat_persistence.dart
import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/models/chat_message.dart';
import 'package:mindcore_ai/models/conversation_meta.dart';
import 'package:mindcore_ai/services/chat_firestore_service.dart';

class ChatPersistence {
  static const _idxKey = 'chat_conversations_index';
  static String _histKey(String id) => 'chat_history_$id';

  // ── Conversation index ──────────────────────────────────────────────────

  static Future<List<ConversationMeta>> listConversations() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_idxKey);
    if (raw == null || raw.isEmpty) return [];
    try {
      final parsed = jsonDecode(raw);
      if (parsed is! List) return [];
      final data = parsed
          .where((e) => e is Map)
          .map<ConversationMeta>(
            (e) => ConversationMeta.fromJson(Map<String, dynamic>.from(e as Map)),
          )
          .toList();
      data.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
      return data;
    } catch (_) {
      return [];
    }
  }

  static Future<void> _saveIndex(List<ConversationMeta> metas) async {
    final byId = <String, ConversationMeta>{};
    for (final m in metas) {
      byId[m.id] = m;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_idxKey, jsonEncode(byId.values.map((m) => m.toJson()).toList()));

    // Cloud sync index entries in background (best effort)
    for (final m in byId.values) {
      unawaited(
        ChatFirestoreService.instance.upsertConversation(
          id: m.id,
          title: m.title,
          updatedAt: m.updatedAt,
          lastText: m.lastText ?? '',
        ),
      );
    }
  }

  static Future<ConversationMeta> createConversation({
    required String id,
    required String title,
  }) async {
    final metas = await listConversations();
    final meta = ConversationMeta(
      id: id,
      title: title,
      updatedAt: DateTime.now(),
      lastText: '',
    );
    metas.add(meta);
    await _saveIndex(metas);
    return meta;
  }

  static Future<void> renameConversation({
    required String id,
    required String title,
  }) async {
    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == id);
    if (i == -1) return;
    metas[i] = metas[i].copyWith(title: title, updatedAt: DateTime.now());
    await _saveIndex(metas);
  }

  static Future<void> deleteConversation(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final metas = await listConversations();
    final before = metas.length;
    metas.removeWhere((m) => m.id == id);
    if (metas.length != before) {
      final byId = <String, ConversationMeta>{};
      for (final m in metas) {
        byId[m.id] = m;
      }
      await prefs.setString(
          _idxKey, jsonEncode(byId.values.map((m) => m.toJson()).toList()));
    }
    await prefs.remove(_histKey(id));
    unawaited(ChatFirestoreService.instance.deleteConversation(id));
  }

  // ── History per conversation ────────────────────────────────────────────

  static Future<List<ChatMessage>> load(String conversationId) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_histKey(conversationId));
    if (raw == null || raw.isEmpty) return [];
    try {
      final parsed = jsonDecode(raw);
      if (parsed is! List) return [];
      return parsed
          .where((e) => e is Map)
          .map<ChatMessage>(
            (e) => ChatMessage.fromJson(Map<String, dynamic>.from(e as Map)),
          )
          .toList();
    } catch (_) {
      return [];
    }
  }

  static Future<void> save(
    String conversationId,
    List<ChatMessage> messages,
  ) async {
    final prefs = await SharedPreferences.getInstance();
    final payload = messages.map((m) => m.toJson()).toList();
    await prefs.setString(_histKey(conversationId), jsonEncode(payload));

    // Touch index timestamp + store preview
    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == conversationId);
    if (i != -1) {
      String preview = '';
      for (var j = messages.length - 1; j >= 0; j--) {
        final t = messages[j].text.trim();
        if (t.isNotEmpty) {
          preview = _firstLine(t);
          break;
        }
      }
      metas[i] = metas[i].copyWith(
        updatedAt: DateTime.now(),
        lastText: preview,
      );
      await _saveIndex(metas);
    }

    // Cloud sync messages (best effort, background)
    unawaited(
      ChatFirestoreService.instance.saveMessages(
        convId: conversationId,
        messages: payload,
      ),
    );
  }

  static Future<void> clear(String conversationId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_histKey(conversationId));
    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == conversationId);
    if (i != -1) {
      metas[i] = metas[i].copyWith(updatedAt: DateTime.now(), lastText: '');
      await _saveIndex(metas);
    }
    unawaited(
      ChatFirestoreService.instance.saveMessages(
        convId: conversationId,
        messages: [],
      ),
    );
  }

  /// Ensure at least one conversation exists; return its id.
  static Future<String> ensureDefault() async {
    final metas = await listConversations();
    if (metas.isNotEmpty) return metas.first.id;
    const defaultId = 'conv-1';
    await createConversation(id: defaultId, title: 'Chat 1');
    return defaultId;
  }

  // ── Auto-title support ──────────────────────────────────────────────────

  static Future<void> autoTitleIfUntitled({
    required String id,
    required String seed,
    String? prefix,
  }) async {
    String cleaned = seed.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (cleaned.isEmpty) return;

    final sentenceEnd = cleaned.indexOf(RegExp(r'[.!?]'));
    if (sentenceEnd != -1 && sentenceEnd < 60) {
      cleaned = cleaned.substring(0, sentenceEnd + 1);
    }
    if (cleaned.length > 40) {
      cleaned = '${cleaned.substring(0, 40).trimRight()}\u2026';
    }
    if (cleaned.isNotEmpty) {
      cleaned = cleaned[0].toUpperCase() + cleaned.substring(1);
    }
    if (prefix != null && prefix.isNotEmpty) {
      final trimmed = cleaned.trimLeft();
      if (!trimmed.startsWith(prefix)) cleaned = '$prefix $cleaned';
    }

    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == id);
    if (i == -1) return;

    final current = metas[i].title.trim().toLowerCase();
    final looksUntitled = current == 'chat' ||
        current.startsWith('chat ') ||
        current == 'untitled' ||
        current.isEmpty;

    if (looksUntitled) {
      metas[i] = metas[i].copyWith(title: cleaned, updatedAt: DateTime.now());
      await _saveIndex(metas);
    }
  }

  // ── Cloud sync ──────────────────────────────────────────────────────────

  static Future<void> syncFromFirestore() async {
    try {
      final remoteMetas =
          await ChatFirestoreService.instance.getConversations();
      if (remoteMetas.isEmpty) return;

      final localMetas = await listConversations();
      final byId = <String, ConversationMeta>{
        for (final m in localMetas) m.id: m,
      };

      final prefs = await SharedPreferences.getInstance();

      for (final raw in remoteMetas) {
        final id = (raw['id'] as String?)?.trim() ?? '';
        if (id.isEmpty) continue;

        final tsAny = raw['updatedAt'];
        final updatedAt = tsAny is DateTime
            ? tsAny
            : (tsAny?.toDate?.call() ?? DateTime.now());

        final title = (raw['title'] as String?) ?? 'Chat';
        final lastText = (raw['lastText'] as String?) ?? '';

        final existing = byId[id];
        if (existing == null || updatedAt.isAfter(existing.updatedAt)) {
          byId[id] = ConversationMeta(
            id: id,
            title: title,
            updatedAt: updatedAt,
            lastText: lastText,
          );

          final msgs = await ChatFirestoreService.instance.getMessages(id);
          if (msgs.isNotEmpty) {
            await prefs.setString(_histKey(id), jsonEncode(msgs));
          }
        }
      }

      final merged = byId.values.toList()
        ..sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
      await prefs.setString(
          _idxKey, jsonEncode(merged.map((m) => m.toJson()).toList()));

      if (kDebugMode) {
        print(
            'ChatPersistence: Firestore \u2192 local merge sync complete (${merged.length} conversations)');
      }
    } catch (e) {
      if (kDebugMode) print('ChatPersistence: syncFromFirestore failed \u2192 $e');
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────────

  static String _firstLine(String s) => s.trim().split('\n').first.trim();
}
