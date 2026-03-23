// lib/pages/helpers/chat_persistence.dart
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/models/chat_message.dart';
import 'package:mindcore_ai/models/conversation_meta.dart';

class ChatPersistence {
  static const _idxKey = "chat_conversations_index";
  static String _histKey(String id) => "chat_history_$id";

  // ===== Conversation index =====
  static Future<List<ConversationMeta>> listConversations() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_idxKey);
    if (raw == null || raw.isEmpty) return [];

    try {
      final parsed = jsonDecode(raw);
      if (parsed is! List) return [];
      final data = parsed
          .where((e) => e is Map)
          .map<ConversationMeta>((e) => ConversationMeta.fromJson(
        Map<String, dynamic>.from(e as Map),
      ))
          .toList();

      // newest first
      data.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
      return data;
    } catch (_) {
      return [];
    }
  }

  static Future<void> _saveIndex(List<ConversationMeta> metas) async {
    // Ensure no duplicate IDs (keep the last occurrence / latest write)
    final byId = <String, ConversationMeta>{};
    for (final m in metas) {
      byId[m.id] = m;
    }
    final prefs = await SharedPreferences.getInstance();
    final payload = byId.values.map((m) => m.toJson()).toList();
    await prefs.setString(_idxKey, jsonEncode(payload));
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
      await _saveIndex(metas);
    }
    await prefs.remove(_histKey(id));
  }

  // ===== History per conversation =====
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

    // Touch index timestamp + store preview of the last *non-empty* message
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
  }

  static Future<void> clear(String conversationId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_histKey(conversationId));

    // Also clear preview text and bump timestamp so UI refreshes
    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == conversationId);
    if (i != -1) {
      metas[i] = metas[i].copyWith(
        updatedAt: DateTime.now(),
        lastText: '',
      );
      await _saveIndex(metas);
    }
  }

  /// Ensure at least one conversation exists; return its id.
  static Future<String> ensureDefault() async {
    final metas = await listConversations();
    if (metas.isNotEmpty) return metas.first.id;
    const defaultId = "conv-1";
    await createConversation(id: defaultId, title: "Chat 1");
    return defaultId;
  }

  // ===== Auto-title support =====
  static Future<void> autoTitleIfUntitled({
    required String id,
    required String seed,
    String? prefix, // optional emoji prefix
  }) async {
    String cleaned = seed.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (cleaned.isEmpty) return;

    final sentenceEnd = cleaned.indexOf(RegExp(r'[.!?]'));
    if (sentenceEnd != -1 && sentenceEnd < 60) {
      cleaned = cleaned.substring(0, sentenceEnd + 1);
    }
    if (cleaned.length > 40) {
      cleaned = "${cleaned.substring(0, 40).trimRight()}…";
    }
    if (cleaned.isNotEmpty) {
      cleaned = cleaned[0].toUpperCase() + cleaned.substring(1);
    }
    if (prefix != null && prefix.isNotEmpty) {
      final trimmed = cleaned.trimLeft();
      if (!trimmed.startsWith(prefix)) cleaned = "$prefix $cleaned";
    }

    final metas = await listConversations();
    final i = metas.indexWhere((m) => m.id == id);
    if (i == -1) return;

    final current = metas[i].title.trim().toLowerCase();
    final looksUntitled =
        current == 'chat' ||
            current.startsWith('chat ') ||
            current == 'untitled' ||
            current.isEmpty;

    if (looksUntitled) {
      metas[i] = metas[i].copyWith(title: cleaned, updatedAt: DateTime.now());
      await _saveIndex(metas);
    }
  }

  // ---------- helpers ----------
  static String _firstLine(String s) {
    final one = s.trim().split('\n').first.trim();
    return one;
  }
}
