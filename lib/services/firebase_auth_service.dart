// lib/services/firebase_auth_service.dart
import 'dart:developer' as dev;

import 'package:firebase_auth/firebase_auth.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import 'package:mindcore_ai/services/sync_coordinator.dart';

class FirebaseAuthService {
  FirebaseAuthService._();
  static final FirebaseAuthService instance = FirebaseAuthService._();

  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: <String>['email', 'profile'],
  );

  // ---------------------------------------------------------------------------
  // Auth state helpers
  // ---------------------------------------------------------------------------

  User? get currentUser => _auth.currentUser;
  Stream<User?> authStateChanges() => _auth.authStateChanges();

  /// True when the current session is an anonymous (not-yet-registered) one.
  bool get isAnonymous => _auth.currentUser?.isAnonymous ?? false;

  /// Ensures a Firebase session exists so onboarding and the secure proxy work
  /// before the user creates a real account. Signs in anonymously if nobody is
  /// signed in yet. Requires the Anonymous provider to be enabled in Firebase.
  Future<User> ensureSignedIn() async {
    final existing = _auth.currentUser;
    if (existing != null) return existing;
    final cred = await _auth.signInAnonymously();
    final user = cred.user;
    if (user == null) {
      throw FirebaseAuthException(
        code: 'anonymous-sign-in-failed',
        message: 'Could not start a session.',
      );
    }
    return user;
  }

  // ---------------------------------------------------------------------------
  // ✅ Auto-sync hook (best effort)
  // ---------------------------------------------------------------------------

  Future<void> _autoSyncAfterLogin() async {
    try {
      // Option 1 (recommended): Coordinator (runs once per uid)
      await SyncCoordinator.instance.syncAfterLogin();

      // Option 2 (if you prefer direct call instead of coordinator):
      // await JournalService.syncFromFirestore(limit: 200);

      // Later:
      // await MoodLogService.syncFromFirestore();
    } catch (e) {
      dev.log('❌ Auto-sync after login failed: $e');
      // Best effort: do NOT throw, login must still succeed
    }
  }

  // ---------------------------------------------------------------------------
  // Google Sign-In (classic flow)
  // ---------------------------------------------------------------------------

  Future<UserCredential> signInWithGoogle() async {
    final googleUser = await _googleSignIn.signIn();

    if (googleUser == null) {
      throw FirebaseAuthException(
        code: 'google-sign-in-cancelled',
        message: 'Google sign-in was cancelled by the user.',
      );
    }

    final googleAuth = await googleUser.authentication;

    final credential = GoogleAuthProvider.credential(
      idToken: googleAuth.idToken,
      accessToken: googleAuth.accessToken,
    );

    final cred = await _auth.signInWithCredential(credential);

    final user = cred.user;
    if (user != null) {
      await _upsertUserDocument(user);
      await _autoSyncAfterLogin(); // ✅ AUTO SYNC HERE
    }

    return cred;
  }

  // ---------------------------------------------------------------------------
  // Email & Password Auth
  // ---------------------------------------------------------------------------

  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) async {
    final cred = await _auth.signInWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );

    final user = cred.user;
    if (user != null) {
      await _upsertUserDocument(user);
      await _autoSyncAfterLogin(); // ✅ AUTO SYNC HERE
    }

    return cred;
  }

  Future<UserCredential> signUpWithEmail({
    required String email,
    required String password,
  }) async {
    final cred = await _auth.createUserWithEmailAndPassword(
      email: email.trim(),
      password: password,
    );

    final user = cred.user;
    if (user != null) {
      await _upsertUserDocument(user);
      await _autoSyncAfterLogin(); // ✅ AUTO SYNC HERE
    }

    return cred;
  }

  Future<void> sendPasswordResetEmail(String email) async {
    await _auth.sendPasswordResetEmail(email: email.trim());
  }

  // ---------------------------------------------------------------------------
  // Upgrade an anonymous session to a real account (link), preserving the same
  // uid so the trial and any data carry over. Falls back to a normal sign-in if
  // that account already exists (e.g. a returning user). Safe to call whether
  // or not the current session is anonymous.
  // ---------------------------------------------------------------------------

  Future<UserCredential> linkOrSignInWithGoogle() async {
    final googleUser = await _googleSignIn.signIn();
    if (googleUser == null) {
      throw FirebaseAuthException(
        code: 'google-sign-in-cancelled',
        message: 'Google sign-in was cancelled by the user.',
      );
    }
    final googleAuth = await googleUser.authentication;
    final credential = GoogleAuthProvider.credential(
      idToken: googleAuth.idToken,
      accessToken: googleAuth.accessToken,
    );

    final current = _auth.currentUser;
    UserCredential cred;
    if (current != null && current.isAnonymous) {
      try {
        cred = await current.linkWithCredential(credential);
      } on FirebaseAuthException catch (e) {
        // The Google account already exists as its own account — sign into it.
        if (e.code == 'credential-already-in-use' ||
            e.code == 'email-already-in-use') {
          cred = await _auth.signInWithCredential(credential);
        } else {
          rethrow;
        }
      }
    } else {
      cred = await _auth.signInWithCredential(credential);
    }

    final user = cred.user;
    if (user != null) {
      await _upsertUserDocument(user);
      await _autoSyncAfterLogin();
    }
    return cred;
  }

  Future<UserCredential> linkOrSignInWithEmail({
    required String email,
    required String password,
  }) async {
    final credential = EmailAuthProvider.credential(
      email: email.trim(),
      password: password,
    );

    final current = _auth.currentUser;
    UserCredential cred;
    if (current != null && current.isAnonymous) {
      try {
        cred = await current.linkWithCredential(credential);
      } on FirebaseAuthException catch (e) {
        // That email already has an account — sign into it instead.
        if (e.code == 'email-already-in-use' ||
            e.code == 'credential-already-in-use') {
          cred = await _auth.signInWithEmailAndPassword(
            email: email.trim(),
            password: password,
          );
        } else {
          rethrow;
        }
      }
    } else {
      cred = await _auth.signInWithEmailAndPassword(
        email: email.trim(),
        password: password,
      );
    }

    final user = cred.user;
    if (user != null) {
      await _upsertUserDocument(user);
      await _autoSyncAfterLogin();
    }
    return cred;
  }

  // ---------------------------------------------------------------------------
  // Account / Profile
  // ---------------------------------------------------------------------------

  Future<void> updateDisplayName(String name) async {
    final user = _auth.currentUser;
    if (user == null) return;
    await user.updateDisplayName(name);
    await user.reload();
  }

  Future<void> updatePhotoUrl(String url) async {
    final user = _auth.currentUser;
    if (user == null) return;
    await user.updatePhotoURL(url);
    await user.reload();
  }

  Future<void> deleteAccount() async {
    final user = _auth.currentUser;
    if (user == null) return;
    await user.delete();
  }

  // ---------------------------------------------------------------------------
  // Sign-out (Google + Firebase)
  // ---------------------------------------------------------------------------

  Future<void> signOut() async {
    try {
      await _googleSignIn.signOut();
    } catch (_) {
      // ignore
    }
    await _auth.signOut();

    // ✅ Reset sync state so next login will sync again
    SyncCoordinator.instance.reset();
  }

  // ---------------------------------------------------------------------------
  // Firestore user doc (users/{uid})
  // ---------------------------------------------------------------------------

  Future<void> _upsertUserDocument(User user) async {
    final docRef = _firestore.collection('users').doc(user.uid);

    final providerId = user.providerData.isNotEmpty
        ? user.providerData.first.providerId
        : (user.isAnonymous ? 'anonymous' : 'password');

    final now = FieldValue.serverTimestamp();

    final data = <String, dynamic>{
      'email': user.email,
      'displayName': user.displayName,
      'photoURL': user.photoURL,
      'providerId': providerId,
      'lastLoginAt': now,
      'updatedAt': now,
    };

    final snap = await docRef.get();
    if (snap.exists) {
      await docRef.update(data);
    } else {
      await docRef.set({
        ...data,
        'createdAt': now,
      });
    }
  }
}
