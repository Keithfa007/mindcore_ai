import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class MoodFirestoreService {
  MoodFirestoreService._();
  static final MoodFirestoreService instance = MoodFirestoreService._();

  final FirebaseFirestore _firestore = FirebaseFirestore.instance;
  final FirebaseAuth _auth = FirebaseAuth.instance;

  CollectionReference<Map<String, dynamic>> _moodCollection() {
    final user = _auth.currentUser;
    if (user == null) {
      throw StateError('No logged-in user. Cannot sync moods to Firestore.');
    }
    return _firestore.collection('users').doc(user.uid).collection('moods');
  }

  /// ✅ New format (preferred)
  Future<void> logMoodV2({
    required String emoji,
    required String label,
    required int score,
    String? note,
    DateTime? timestamp,
  }) async {
    await _moodCollection().add({
      'emoji': emoji,
      'label': label,
      'score': score,
      'note': note,
      'timestamp': Timestamp.fromDate(timestamp ?? DateTime.now()),
    });
  }

  /// ✅ Old format (kept so nothing breaks)
  Future<void> logMood({
    required String mood,
    required int score,
    String? note,
    DateTime? timestamp,
  }) async {
    await _moodCollection().add({
      'mood': mood,
      'score': score,
      'note': note,
      'timestamp': Timestamp.fromDate(timestamp ?? DateTime.now()),
    });
  }

  Future<List<Map<String, dynamic>>> getRecentMoods({int limit = 50}) async {
    final snap = await _moodCollection()
        .orderBy('timestamp', descending: true)
        .limit(limit)
        .get();

    return snap.docs
        .map((doc) => {'id': doc.id, ...doc.data()})
        .toList();
  }
}
