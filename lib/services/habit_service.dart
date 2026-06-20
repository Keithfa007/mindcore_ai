// lib/services/habit_service.dart
//
// Daily habit tracking — exercise, hydration, medication, sleep.
// Stored in Firestore: users/{uid}/habits/{YYYY-MM-DD}

import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart';

class HabitEntry {
  final String date; // YYYY-MM-DD
  final bool exercise;
  final bool hydration;
  final bool medication;
  final bool sleep;

  const HabitEntry({
    required this.date,
    this.exercise = false,
    this.hydration = false,
    this.medication = false,
    this.sleep = false,
  });

  int get completedCount =>
      (exercise ? 1 : 0) + (hydration ? 1 : 0) + (medication ? 1 : 0) + (sleep ? 1 : 0);

  double get completionPercent => completedCount / 4.0;

  Map<String, dynamic> toMap() => {
    'exercise': exercise,
    'hydration': hydration,
    'medication': medication,
    'sleep': sleep,
    'updatedAt': FieldValue.serverTimestamp(),
  };

  factory HabitEntry.fromMap(String date, Map<String, dynamic> data) => HabitEntry(
    date: date,
    exercise: data['exercise'] as bool? ?? false,
    hydration: data['hydration'] as bool? ?? false,
    medication: data['medication'] as bool? ?? false,
    sleep: data['sleep'] as bool? ?? false,
  );

  HabitEntry copyWith({bool? exercise, bool? hydration, bool? medication, bool? sleep}) =>
      HabitEntry(
        date: date,
        exercise: exercise ?? this.exercise,
        hydration: hydration ?? this.hydration,
        medication: medication ?? this.medication,
        sleep: sleep ?? this.sleep,
      );
}

class HabitService {
  HabitService._();

  static final _firestore = FirebaseFirestore.instance;

  static String _todayKey() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }

  static String? get _uid => FirebaseAuth.instance.currentUser?.uid;

  static DocumentReference? _docRef(String date) {
    final uid = _uid;
    if (uid == null) return null;
    return _firestore.collection('users').doc(uid).collection('habits').doc(date);
  }

  /// Get today's habit entry (or defaults if none exists).
  static Future<HabitEntry> getToday() async {
    final date = _todayKey();
    final ref = _docRef(date);
    if (ref == null) return HabitEntry(date: date);
    try {
      final doc = await ref.get();
      if (!doc.exists) return HabitEntry(date: date);
      return HabitEntry.fromMap(date, doc.data() as Map<String, dynamic>);
    } catch (_) {
      return HabitEntry(date: date);
    }
  }

  /// Save a habit entry for today.
  static Future<void> saveToday(HabitEntry entry) async {
    final ref = _docRef(entry.date);
    if (ref == null) return;
    await ref.set(entry.toMap(), SetOptions(merge: true));
  }

  /// Toggle a specific habit and save.
  static Future<HabitEntry> toggle(HabitEntry current, String habit) async {
    HabitEntry updated;
    switch (habit) {
      case 'exercise':
        updated = current.copyWith(exercise: !current.exercise);
        break;
      case 'hydration':
        updated = current.copyWith(hydration: !current.hydration);
        break;
      case 'medication':
        updated = current.copyWith(medication: !current.medication);
        break;
      case 'sleep':
        updated = current.copyWith(sleep: !current.sleep);
        break;
      default:
        return current;
    }
    await saveToday(updated);
    return updated;
  }

  /// Get habit entries for the last N days (for trend/history).
  static Future<List<HabitEntry>> getHistory({int days = 7}) async {
    final uid = _uid;
    if (uid == null) return [];

    final entries = <HabitEntry>[];
    final now = DateTime.now();

    for (int i = 0; i < days; i++) {
      final date = now.subtract(Duration(days: i));
      final key = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
      try {
        final doc = await _firestore
            .collection('users').doc(uid)
            .collection('habits').doc(key)
            .get();
        if (doc.exists) {
          entries.add(HabitEntry.fromMap(key, doc.data()!));
        } else {
          entries.add(HabitEntry(date: key));
        }
      } catch (_) {
        entries.add(HabitEntry(date: key));
      }
    }

    return entries;
  }
}
