// lib/services/truth_deck_service.dart
//
// Manages daily Truth Deck card selection and engagement tracking.
// One card per day, deterministic (same card all day, changes at midnight).
// No API calls — all local via SharedPreferences.

import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/data/truth_deck_data.dart';

class TruthDeckService {
  TruthDeckService._();

  static const _kLastDate = 'truth_deck_last_date';
  static const _kCardIndex = 'truth_deck_card_index';
  static const _kTotalSeen = 'truth_deck_total_seen';
  static const _kTotalTalked = 'truth_deck_total_talked';

  /// Returns today's card index, advancing to the next card if the day changed.
  static Future<int> todayCardIndex() async {
    final prefs = await SharedPreferences.getInstance();
    final today = _todayKey();
    final lastDate = prefs.getString(_kLastDate);

    if (lastDate == today) {
      // Same day — return stored index
      return prefs.getInt(_kCardIndex) ?? 0;
    }

    // New day — advance to next card
    final prevIndex = prefs.getInt(_kCardIndex) ?? -1;
    final nextIndex = (prevIndex + 1) % truthDeckCards.length;

    await prefs.setString(_kLastDate, today);
    await prefs.setInt(_kCardIndex, nextIndex);

    return nextIndex;
  }

  /// Returns today's card text.
  static Future<String> todayCard() async {
    final idx = await todayCardIndex();
    return truthDeckCards[idx];
  }

  /// Whether the user has already seen today's card.
  static Future<bool> hasSeenToday() async {
    final prefs = await SharedPreferences.getInstance();
    final today = _todayKey();
    return prefs.getString(_kLastDate) == today;
  }

  /// Record that the user viewed a card ("Sit with this").
  static Future<void> recordSeen() async {
    final prefs = await SharedPreferences.getInstance();
    final total = prefs.getInt(_kTotalSeen) ?? 0;
    await prefs.setInt(_kTotalSeen, total + 1);
  }

  /// Record that the user tapped "Talk about this".
  static Future<void> recordTalked() async {
    final prefs = await SharedPreferences.getInstance();
    final total = prefs.getInt(_kTotalTalked) ?? 0;
    await prefs.setInt(_kTotalTalked, total + 1);
  }

  /// Stats for future analytics.
  static Future<Map<String, int>> stats() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'totalSeen': prefs.getInt(_kTotalSeen) ?? 0,
      'totalTalked': prefs.getInt(_kTotalTalked) ?? 0,
    };
  }

  static String _todayKey() {
    final now = DateTime.now();
    return '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }
}
