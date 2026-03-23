// lib/pages/helpers/journal_service.dart
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import 'package:mindcore_ai/services/journal_firestore_service.dart';

class JournalEntry {
  final String id; // stable id for Firestore doc
  final DateTime timestamp;
  final String note;

  JournalEntry({
    required this.id,
    required this.timestamp,
    required this.note,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'ts': timestamp.toIso8601String(),
    'note': note,
  };

  static JournalEntry fromJson(Map<String, dynamic> j) {
    final ts = DateTime.tryParse(j['ts'] as String? ?? '') ?? DateTime.now();
    final note = (j['note'] as String?)?.trim() ?? '';

    final id = (j['id'] as String?)?.trim();
    final safeId = (id != null && id.isNotEmpty) ? id : ts.millisecondsSinceEpoch.toString();

    return JournalEntry(id: safeId, timestamp: ts, note: note);
  }
}

/// ✅ Record-free result (works on older Dart)
class JournalAddResult {
  final JournalEntry entry;
  final bool cloudOk;
  const JournalAddResult(this.entry, this.cloudOk);
}

class JournalService {
  static const String _kStore = 'journal_entries';
  static const List<String> _legacy = ['journal_entries_v2', 'journalEntries'];

  static Future<List<JournalEntry>> getEntries() async {
    final prefs = await SharedPreferences.getInstance();

    final raw = prefs.getString(_kStore);
    if (raw != null && raw.isNotEmpty) {
      try {
        final list = (jsonDecode(raw) as List)
            .map((e) => JournalEntry.fromJson(Map<String, dynamic>.from(e)))
            .toList()
          ..sort((a, b) => b.timestamp.compareTo(a.timestamp));
        return list;
      } catch (e) {
        if (kDebugMode) print('JournalService: parse $_kStore failed → $e');
      }
    }

    for (final key in _legacy) {
      final old = prefs.getString(key);
      if (old == null || old.isEmpty) continue;
      try {
        final list = (jsonDecode(old) as List)
            .map((e) => Map<String, dynamic>.from(e))
            .map((m) {
          final tsStr = (m['ts'] as String?) ?? (m['timestamp'] as String?) ?? '';
          final note = (m['note'] as String?) ?? (m['text'] as String?) ?? '';
          final ts = DateTime.tryParse(tsStr) ?? DateTime.now();

          final id = (m['id'] as String?)?.trim();
          final safeId = (id != null && id.isNotEmpty)
              ? id
              : ts.millisecondsSinceEpoch.toString();

          return JournalEntry(
            id: safeId,
            timestamp: ts,
            note: note.trim(),
          );
        })
            .toList()
          ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

        await prefs.setString(_kStore, jsonEncode(list.map((e) => e.toJson()).toList()));
        if (kDebugMode) print('JournalService: migrated ${list.length} from $key → $_kStore');
        return list;
      } catch (e) {
        if (kDebugMode) print('JournalService: parse $key failed → $e');
      }
    }

    return <JournalEntry>[];
  }

  static Future<void> _saveAll(List<JournalEntry> entries) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kStore, jsonEncode(entries.map((e) => e.toJson()).toList()));
  }

  /// ✅ Adds entry locally, then tries cloud sync.
  /// Returns (entry + cloudOk) via JournalAddResult (no records needed).
  static Future<JournalAddResult> addEntry(String note, {DateTime? when}) async {
    final trimmed = note.trim();
    final now = when ?? DateTime.now();

    final newEntry = JournalEntry(
      id: now.millisecondsSinceEpoch.toString(),
      timestamp: now,
      note: trimmed,
    );

    // 1) Local save first
    final current = await getEntries(); // newest → oldest
    final updated = <JournalEntry>[newEntry, ...current];
    await _saveAll(updated);

    // 2) Cloud sync (best effort)
    bool cloudOk = false;
    if (trimmed.isNotEmpty) {
      try {
        await JournalFirestoreService.instance.upsertEntry(
          id: newEntry.id,
          text: newEntry.note,
          createdAt: newEntry.timestamp,
          updatedAt: DateTime.now(),
        );
        cloudOk = true;
      } catch (e) {
        if (kDebugMode) print('JournalService: Firestore add failed → $e');
      }
    }

    return JournalAddResult(newEntry, cloudOk);
  }

  static Future<bool> updateEntry(DateTime timestamp, String updatedNote) async {
    final all = await getEntries();

    final next = <JournalEntry>[];
    JournalEntry? updatedEntry;

    for (final e in all) {
      if (updatedEntry == null && e.timestamp.isAtSameMomentAs(timestamp)) {
        updatedEntry = JournalEntry(
          id: e.id,
          timestamp: e.timestamp,
          note: updatedNote.trim(),
        );
        next.add(updatedEntry);
      } else {
        next.add(e);
      }
    }

    if (updatedEntry == null) return false;

    await _saveAll(next);

    try {
      await JournalFirestoreService.instance.upsertEntry(
        id: updatedEntry.id,
        text: updatedEntry.note,
        createdAt: updatedEntry.timestamp,
        updatedAt: DateTime.now(),
      );
    } catch (e) {
      if (kDebugMode) print('JournalService: Firestore update failed → $e');
    }

    return true;
  }

  static Future<JournalEntry?> deleteEntry(DateTime timestamp) async {
    final all = await getEntries();

    JournalEntry? removed;
    final next = <JournalEntry>[];

    for (final e in all) {
      if (removed == null && e.timestamp.isAtSameMomentAs(timestamp)) {
        removed = e;
        continue;
      }
      next.add(e);
    }

    if (removed == null) return null;

    await _saveAll(next);

    try {
      await JournalFirestoreService.instance.deleteEntry(removed.id);
    } catch (e) {
      if (kDebugMode) print('JournalService: Firestore delete failed → $e');
    }

    return removed;
  }

  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kStore);
  }

  static Future<List<JournalEntry>> getEntriesInRange(DateTime start, DateTime end) async {
    final all = await getEntries();
    final s = DateTime(start.year, start.month, start.day);
    final e = DateTime(end.year, end.month, end.day, 23, 59, 59, 999);
    return all.where((j) => !j.timestamp.isBefore(s) && !j.timestamp.isAfter(e)).toList();
  }

  static Future<void> syncFromFirestore({int limit = 200}) async {
    try {
      final remote = await JournalFirestoreService.instance.getRecent(limit: limit);
      if (remote.isEmpty) return;

      final local = await getEntries();
      final byId = <String, JournalEntry>{for (final e in local) e.id: e};

      for (final m in remote) {
        final createdAny = m['createdAt'];
        final createdAt = createdAny is Timestamp ? createdAny.toDate() : DateTime.now();

        final idRaw = (m['id'] ?? '').toString().trim();
        final id = idRaw.isNotEmpty ? idRaw : createdAt.millisecondsSinceEpoch.toString();

        final text = (m['text'] ?? '').toString().trim();

        byId[id] = JournalEntry(id: id, timestamp: createdAt, note: text);
      }

      final merged = byId.values.toList()
        ..sort((a, b) => b.timestamp.compareTo(a.timestamp));

      await _saveAll(merged);

      if (kDebugMode) {
        print('JournalService: Firestore → local merge sync complete (${merged.length})');
      }
    } catch (e) {
      if (kDebugMode) print('JournalService: Firestore sync failed → $e');
    }
  }
}
