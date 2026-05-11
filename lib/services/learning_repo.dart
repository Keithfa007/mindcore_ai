import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import 'package:mindcore_ai/models/learning_topic.dart';
import 'package:mindcore_ai/data/learning_seeds.dart';

class LearningRepo {
  static const _storeKey = 'learning_topics_store_v1';

  // ── Load remote topics from Firestore ────────────────────────────────────────
  static Future<List<LearningTopic>> _loadRemote() async {
    try {
      final snapshot = await FirebaseFirestore.instance
          .collection('learning_items')
          .get();

      final remote = snapshot.docs
          .where((doc) => doc.data()['active'] == true)
          .map((doc) {
            final d         = doc.data();
            final ts        = d['created_at'];
            final createdAt = ts is Timestamp ? ts.toDate() : DateTime.now();
            return LearningTopic(
              id:         'remote_${doc.id}',
              title:      d['title']      ?? '',
              overview:   d['overview']   ?? '',
              examples:   List<String>.from(d['examples']   ?? []),
              strategies: List<String>.from(d['strategies'] ?? []),
              tags:       List<String>.from(d['tags']       ?? []),
              isNew:      d['is_new']     ?? false,
              createdAt:  createdAt,
            );
          })
          .toList();

      // Newest remote items first
      remote.sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (kDebugMode) debugPrint('Learning: loaded ${remote.length} remote item(s)');
      return remote;
    } catch (e) {
      if (kDebugMode) debugPrint('Learning Firestore error: $e');
      return [];
    }
  }

  // ── Load all topics: remote first, then local seeds ───────────────────────────
  static Future<List<LearningTopic>> load() async {
    final prefs = await SharedPreferences.getInstance();

    // Read saved favorites / metadata
    final raw = prefs.getString(_storeKey);
    final Map<String, Map<String, dynamic>> savedById = {};
    if (raw != null && raw.isNotEmpty) {
      try {
        final parsed = jsonDecode(raw);
        if (parsed is List) {
          for (final e in parsed) {
            if (e is Map) {
              final m  = Map<String, dynamic>.from(e);
              final id = (m['id'] ?? '').toString();
              if (id.isNotEmpty) savedById[id] = m;
            }
          }
        }
      } catch (_) {}
    }

    // Build local topics from seeds
    final List<LearningTopic> localTopics = [];
    for (final s in kLearningSeeds) {
      final saved     = savedById[s.id];
      final isFav     = (saved?['fav'] as bool?) ?? false;
      final createdAt = DateTime.tryParse((saved?['createdAt'] ?? '') as String? ?? '') ?? DateTime.now();
      final updatedAt = DateTime.tryParse((saved?['updatedAt'] ?? '') as String? ?? '') ?? DateTime.now();

      localTopics.add(LearningTopic(
        id:         s.id,
        title:      s.title,
        overview:   s.overview,
        examples:   List<String>.from(s.examples),
        strategies: List<String>.from(s.strategies),
        tags:       List<String>.from(s.tags),
        isFavorite: isFav,
        createdAt:  createdAt,
        updatedAt:  updatedAt,
      ));
    }

    // Load remote topics and restore their favorites from prefs
    final remoteTopics = await _loadRemote();
    for (var i = 0; i < remoteTopics.length; i++) {
      final saved = savedById[remoteTopics[i].id];
      if (saved != null) {
        remoteTopics[i] = remoteTopics[i].copyWith(
          isFavorite: (saved['fav'] as bool?) ?? false,
        );
      }
    }

    // Combine: remote (newest first) + local (alphabetical)
    localTopics.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
    final all = [...remoteTopics, ...localTopics];

    // Persist a normalized snapshot for favorites tracking
    await _saveAll(all);
    return all;
  }

  static Future<void> _saveAll(List<LearningTopic> topics) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _storeKey,
      jsonEncode(topics.map((t) => t.toJson()).toList()),
    );
  }

  static Future<void> setFavorite(String id, bool fav) async {
    final prefs = await SharedPreferences.getInstance();
    final raw   = prefs.getString(_storeKey);
    List<Map<String, dynamic>> list = [];
    if (raw != null && raw.isNotEmpty) {
      try {
        final parsed = jsonDecode(raw);
        if (parsed is List) {
          list = parsed.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        }
      } catch (_) {}
    }

    final i = list.indexWhere((m) => (m['id'] ?? '') == id);
    if (i != -1) {
      list[i]['fav']       = fav;
      list[i]['updatedAt'] = DateTime.now().toIso8601String();
    } else {
      // Remote item not yet in store — seed it
      list.add({
        'id':         id,
        'fav':        fav,
        'createdAt':  DateTime.now().toIso8601String(),
        'updatedAt':  DateTime.now().toIso8601String(),
      });
    }

    await prefs.setString(_storeKey, jsonEncode(list));
  }
}
