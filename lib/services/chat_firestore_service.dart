// lib/services/chat_firestore_service.dart
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';

/// Firestore layout:
///   users/{uid}/chat_conversations/{convId}  — index doc
///   users/{uid}/chat_messages/{convId}       — messages doc (field: messages[])
class ChatFirestoreService {
  ChatFirestoreService._();
  static final instance = ChatFirestoreService._();

  FirebaseFirestore get _db => FirebaseFirestore.instance;
  String? get _uid => FirebaseAuth.instance.currentUser?.uid;

  CollectionReference<Map<String, dynamic>>? _convCol() {
    final uid = _uid;
    if (uid == null) return null;
    return _db.collection('users').doc(uid).collection('chat_conversations');
  }

  DocumentReference<Map<String, dynamic>>? _msgDoc(String convId) {
    final uid = _uid;
    if (uid == null) return null;
    return _db.collection('users').doc(uid).collection('chat_messages').doc(convId);
  }

  // ── Conversation index ──────────────────────────────────────────────────

  Future<void> upsertConversation({
    required String id,
    required String title,
    required DateTime updatedAt,
    required String lastText,
  }) async {
    try {
      final col = _convCol();
      if (col == null) return;
      await col.doc(id).set({
        'id': id,
        'title': title,
        'updatedAt': Timestamp.fromDate(updatedAt),
        'lastText': lastText,
      }, SetOptions(merge: true));
    } catch (e) {
      if (kDebugMode) print('ChatFirestoreService: upsertConversation failed → $e');
    }
  }

  Future<void> deleteConversation(String id) async {
    try {
      await _convCol()?.doc(id).delete();
      await _msgDoc(id)?.delete();
    } catch (e) {
      if (kDebugMode) print('ChatFirestoreService: deleteConversation failed → $e');
    }
  }

  Future<List<Map<String, dynamic>>> getConversations({int limit = 100}) async {
    try {
      final col = _convCol();
      if (col == null) return [];
      final snap = await col
          .orderBy('updatedAt', descending: true)
          .limit(limit)
          .get();
      return snap.docs.map((d) => d.data()).toList();
    } catch (e) {
      if (kDebugMode) print('ChatFirestoreService: getConversations failed → $e');
      return [];
    }
  }

  // ── Messages ────────────────────────────────────────────────────────────

  Future<void> saveMessages({
    required String convId,
    required List<Map<String, dynamic>> messages,
  }) async {
    try {
      final doc = _msgDoc(convId);
      if (doc == null) return;
      await doc.set({
        'messages': messages,
        'updatedAt': FieldValue.serverTimestamp(),
      });
    } catch (e) {
      if (kDebugMode) print('ChatFirestoreService: saveMessages failed → $e');
    }
  }

  Future<List<Map<String, dynamic>>> getMessages(String convId) async {
    try {
      final doc = _msgDoc(convId);
      if (doc == null) return [];
      final snap = await doc.get();
      if (!snap.exists) return [];
      final data = snap.data();
      if (data == null) return [];
      final msgs = data['messages'];
      if (msgs is! List) return [];
      return msgs
          .whereType<Map>()
          .map((m) => Map<String, dynamic>.from(m))
          .toList();
    } catch (e) {
      if (kDebugMode) print('ChatFirestoreService: getMessages failed → $e');
      return [];
    }
  }
}
