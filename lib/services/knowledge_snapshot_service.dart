import 'package:mindcore_ai/pages/helpers/journal_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';

class KnowledgeSnapshot {
  final String dominantState;
  final String summary;
  final String recommendedFocus;
  final int recentJournalCount;
  final double recentMoodAverage;

  const KnowledgeSnapshot({
    required this.dominantState,
    required this.summary,
    required this.recommendedFocus,
    required this.recentJournalCount,
    required this.recentMoodAverage,
  });
}

class KnowledgeSnapshotService {
  KnowledgeSnapshotService._();

  static Future<KnowledgeSnapshot> buildSnapshot() async {
    final journals = await JournalService.getEntries();
    final moods = await MoodRepo.instance.fetchAll();

    final recentJournals = journals.take(3).toList();
    final recentMoods = moods.take(7).toList();

    final avgMood = recentMoods.isEmpty
        ? 3.0
        : recentMoods.map((m) => m.score).reduce((a, b) => a + b) / recentMoods.length;

    final dominantState = _dominantState(avgMood);
    final focus = _recommendedFocus(avgMood, recentJournals.length);
    final summary = _buildSummary(
      dominantState: dominantState,
      journalCount: recentJournals.length,
      avgMood: avgMood,
    );

    return KnowledgeSnapshot(
      dominantState: dominantState,
      summary: summary,
      recommendedFocus: focus,
      recentJournalCount: recentJournals.length,
      recentMoodAverage: avgMood,
    );
  }

  static String _dominantState(double avgMood) {
    if (avgMood <= 2.0) return 'low';
    if (avgMood <= 3.0) return 'fragile';
    if (avgMood <= 4.0) return 'steady';
    return 'uplifted';
  }

  static String _recommendedFocus(double avgMood, int journalCount) {
    if (avgMood <= 2.0) return 'grounding';
    if (journalCount == 0) return 'reflection';
    if (avgMood <= 3.0) return 'self-compassion';
    if (avgMood <= 4.0) return 'consistency';
    return 'momentum';
  }

  static String _buildSummary({
    required String dominantState,
    required int journalCount,
    required double avgMood,
  }) {
    final moodLine = avgMood.toStringAsFixed(1);

    switch (dominantState) {
      case 'low':
        return 'Recent mood trend is low (avg $moodLine/5). Prioritize softer support and very small wins.';
      case 'fragile':
        return 'Recent mood trend looks mixed (avg $moodLine/5). Stabilizing routines may help most right now.';
      case 'steady':
        return 'Recent mood trend is fairly steady (avg $moodLine/5). This is a good window for consistency.';
      case 'uplifted':
        return 'Recent mood trend is strong (avg $moodLine/5). You can build gently on this momentum.';
      default:
        return 'Recent journal entries: $journalCount. Recent mood average: $moodLine/5.';
    }
  }
}
