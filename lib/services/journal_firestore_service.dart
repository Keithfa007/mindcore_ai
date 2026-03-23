import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class JournalFirestoreService {
  JournalFirestoreService._();
  static final JournalFirestoreService instance = JournalFirestoreService._();

  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  CollectionReference<Map<String, dynamic>> _journalCol() {
    final user = _auth.currentUser;
    if (user == null) {
      throw StateError('No logged-in user. Cannot sync journal to Firestore.');
    }
    return _firestore.collection('users').doc(user.uid).collection('journal');
  }

  Future<void> upsertEntry({
    required String id,
    required String text,
    String? moodEmoji,
    String? moodLabel,
    required DateTime createdAt,
    DateTime? updatedAt,
  }) async {
    await _journalCol().doc(id).set({
      'text': text,
      'moodEmoji': moodEmoji,
      'moodLabel': moodLabel,
      'createdAt': Timestamp.fromDate(createdAt),
      'updatedAt': Timestamp.fromDate(updatedAt ?? DateTime.now()),
    }, SetOptions(merge: true));
  }

  Future<void> deleteEntry(String id) async {
    await _journalCol().doc(id).delete();
  }

  Future<List<Map<String, dynamic>>> getRecent({int limit = 200}) async {
    final snap = await _journalCol()
        .orderBy('createdAt', descending: true)
        .limit(limit)
        .get();

    return snap.docs.map((d) => {'id': d.id, ...d.data()}).toList();
  }
}
