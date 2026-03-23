import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:mindcore_ai/models/learning_topic.dart';
import 'package:mindcore_ai/data/learning_seeds.dart';

class LearningRepo {
  static const _storeKey = 'learning_topics_store_v1';

  /// Load topics from seeds + merge saved favorites/metadata.
  /// Returns ALL topics, sorted alphabetically by title.
  static Future<List<LearningTopic>> load() async {
    final prefs = await SharedPreferences.getInstance();

    // Read saved topics (for isFavorite + timestamps)
    final raw = prefs.getString(_storeKey);
    final Map<String, Map<String, dynamic>> savedById = {};
    if (raw != null && raw.isNotEmpty) {
      try {
        final parsed = jsonDecode(raw);
        if (parsed is List) {
          for (final e in parsed) {
            if (e is Map) {
              final m = Map<String, dynamic>.from(e);
              final id = (m['id'] ?? '').toString();
              if (id.isNotEmpty) savedById[id] = m;
            }
          }
        }
      } catch (_) {}
    }

    // Build topics from seeds and overlay saved flags/dates
    final List<LearningTopic> topics = [];
    for (final s in kLearningSeeds) {
      final saved = savedById[s.id];
      final isFav = (saved?['fav'] as bool?) ?? false;
      final createdAt = DateTime.tryParse((saved?['createdAt'] ?? '') as String? ?? '') ?? DateTime.now();
      final updatedAt = DateTime.tryParse((saved?['updatedAt'] ?? '') as String? ?? '') ?? DateTime.now();

      topics.add(LearningTopic(
        id: s.id,
        title: s.title,
        overview: s.overview,
        examples: List<String>.from(s.examples),
        strategies: List<String>.from(s.strategies),
        tags: List<String>.from(s.tags),
        isFavorite: isFav,
        createdAt: createdAt,
        updatedAt: updatedAt,
      ));
    }

    // Sort alphabetically by title (stable)
    topics.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));

    // Save a normalized snapshot so future loads are fast/consistent
    await _saveAll(topics);
    return topics;
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
    final raw = prefs.getString(_storeKey);
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
      list[i]['fav'] = fav;
      list[i]['updatedAt'] = DateTime.now().toIso8601String();
    } else {
      // If not found (e.g., first run), seed it from the seeds list
      final seed = kLearningSeeds.firstWhere(
            (s) => s.id == id,
        orElse: () => kLearningSeeds.first,
      );
      list.add({
        'id': seed.id,
        'title': seed.title,
        'overview': seed.overview,
        'examples': seed.examples,
        'strategies': seed.strategies,
        'tags': seed.tags,
        'fav': fav,
        'createdAt': DateTime.now().toIso8601String(),
        'updatedAt': DateTime.now().toIso8601String(),
      });
    }

    await prefs.setString(_storeKey, jsonEncode(list));
  }
}
