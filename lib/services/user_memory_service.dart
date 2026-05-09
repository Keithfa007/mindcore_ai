// lib/services/user_memory_service.dart
//
// Persistent memory system — extracts key facts about the user from
// their conversations and stores them in Firestore so the AI can
// remember who they are across sessions.
//
// HOW IT WORKS:
//   1. After every 5 user messages in chat, saveMemory() is called.
//   2. The last 10 messages are sent to gpt-4o-mini which extracts
//      3–5 key personal facts and returns a short paragraph.
//   3. The paragraph is merged with the existing memory summary
//      (capped at ~300 words) and saved to Firestore.
//   4. getMemorySummary() is called in chat_stream_service.dart
//      before building the system prompt so the AI knows the user.

import 'dart:convert';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import 'package:mindcore_ai/env/env.dart';

class UserMemoryService {
  UserMemoryService._();

  static const _endpoint = 'https://api.openai.com/v1/chat/completions';
  static const _model    = 'gpt-4o-mini';

  // ── Read ────────────────────────────────────────────────────────────────

  static Future<String> getMemorySummary() async {
    try {
      final uid = FirebaseAuth.instance.currentUser?.uid;
      if (uid == null) return '';
      final doc = await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('memory')
          .doc('summary')
          .get();
      if (!doc.exists) return '';
      return (doc.data()?['summary'] as String?) ?? '';
    } catch (_) {
      return '';
    }
  }

  // ── Write ───────────────────────────────────────────────────────────────

  static Future<void> saveMemory(
      List<Map<String, String>> recentMessages) async {
    try {
      final uid    = FirebaseAuth.instance.currentUser?.uid;
      final apiKey = Env.openaiKey;
      if (uid == null || apiKey.trim().isEmpty) return;

      // Need at least 4 messages to extract meaningful facts
      final userMessages =
          recentMessages.where((m) => m['role'] == 'user').length;
      if (userMessages < 2) return;

      final conversationText = recentMessages
          .take(10)
          .map((m) => '${(m['role'] ?? 'user').toUpperCase()}: ${m['content']}'
                      ''.trim())
          .where((s) => s.isNotEmpty)
          .join('\n');

      final response = await http
          .post(
            Uri.parse(_endpoint),
            headers: {
              'Authorization': 'Bearer $apiKey',
              'Content-Type':  'application/json',
            },
            body: jsonEncode({
              'model':       _model,
              'temperature': 0.3,
              'max_tokens':  150,
              'messages': [
                {
                  'role':    'system',
                  'content': 'Extract 3-5 key personal facts about the user '
                             'from this conversation. Include their name if '
                             'mentioned, what they are going through emotionally, '
                             'any significant life context they shared, how they '
                             'are feeling, and anything specific they want support with. '
                             'Write as a short paragraph in second person '
                             '(e.g. "You mentioned...", "You are dealing with..."). '
                             'Max 80 words. Be specific and human. '
                             'Return only the paragraph, no preamble.',
                },
                {'role': 'user', 'content': conversationText},
              ],
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode != 200) return;

      final body    = jsonDecode(response.body) as Map<String, dynamic>?;
      final choices = body?['choices'] as List?;
      final newFact = choices?.isNotEmpty == true
          ? (choices!.first?['message']?['content'] as String?)?.trim()
          : null;

      if (newFact == null || newFact.isEmpty) return;

      // Merge with existing summary — keep last ~300 words
      final existing = await getMemorySummary();
      final merged   = existing.isEmpty ? newFact : '$existing $newFact';
      final words    = merged.split(RegExp(r'\s+'));
      final trimmed  = words.length > 300
          ? words.sublist(words.length - 300).join(' ')
          : merged;

      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('memory')
          .doc('summary')
          .set({
        'summary':   trimmed,
        'updatedAt': FieldValue.serverTimestamp(),
      }, SetOptions(merge: true));
    } catch (_) {
      // Silent fail — memory is enhancement, not critical path
    }
  }

  // ── Clear ───────────────────────────────────────────────────────────────

  static Future<void> clearMemory() async {
    try {
      final uid = FirebaseAuth.instance.currentUser?.uid;
      if (uid == null) return;
      await FirebaseFirestore.instance
          .collection('users')
          .doc(uid)
          .collection('memory')
          .doc('summary')
          .delete();
    } catch (_) {}
  }
}
