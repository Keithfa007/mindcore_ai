import 'dart:developer' as dev;
import 'package:firebase_auth/firebase_auth.dart';

import 'package:mindcore_ai/pages/helpers/journal_service.dart';
// If you already have mood sync: import it too
// import 'package:mindcore_ai/services/mood_firestore_service.dart';
// OR if you made a MoodRepo sync function, import that.

class SyncCoordinator {
  SyncCoordinator._();
  static final SyncCoordinator instance = SyncCoordinator._();

  String? _lastSyncedUid;
  bool _syncInProgress = false;

  /// Call this right after auth becomes non-null.
  /// It will run once per user session (per UID).
  Future<void> syncAfterLogin() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    // Prevent double sync
    if (_syncInProgress) return;
    if (_lastSyncedUid == user.uid) return;

    _syncInProgress = true;
    dev.log('🔄 Auto-sync starting for uid=${user.uid}');

    try {
      // 1) Pull journal from cloud into local
      await JournalService.syncFromFirestore(limit: 200);

      // 2) (Optional) Pull moods too if you have it
      // await MoodLogService.syncFromFirestore(); // if you created it
      // OR implement MoodRepo merge like journal

      _lastSyncedUid = user.uid;
      dev.log('✅ Auto-sync completed for uid=${user.uid}');
    } catch (e) {
      dev.log('❌ Auto-sync failed: $e');
    } finally {
      _syncInProgress = false;
    }
  }

  /// Call on logout if you want to allow sync again next login
  void reset() {
    _lastSyncedUid = null;
    _syncInProgress = false;
  }
}
