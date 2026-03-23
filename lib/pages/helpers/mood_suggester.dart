class MoodSuggestion {
  final String emoji;
  final String label;
  final double confidence;

  const MoodSuggestion({
    required this.emoji,
    required this.label,
    required this.confidence,
  });
}

class MoodSuggester {
  static MoodSuggestion suggest({
    required String userText,
    required String botText,
  }) {
    final t = ('${userText.trim()} ${botText.trim()}').toLowerCase();

    bool hasAny(List<String> keys) => keys.any(t.contains);

    if (hasAny(['panic', 'attack', "can’t breathe", "can't breathe", 'heart racing', 'terrified'])) {
      return const MoodSuggestion(emoji: '😰', label: 'Panic', confidence: 0.85);
    }
    if (hasAny(['anxiety', 'anxious', 'stress', 'stressed', 'overwhelmed', 'overthinking', 'worried', 'worry'])) {
      return const MoodSuggestion(emoji: '😟', label: 'Anxious', confidence: 0.78);
    }
    if (hasAny(['sad', 'depressed', 'low', 'hopeless', 'empty', 'lonely', 'cry', 'crying'])) {
      return const MoodSuggestion(emoji: '😞', label: 'Low', confidence: 0.75);
    }
    if (hasAny(['angry', 'rage', 'furious', 'irritated', 'frustrated'])) {
      return const MoodSuggestion(emoji: '😠', label: 'Frustrated', confidence: 0.72);
    }
    if (hasAny(['sleep', 'insomnia', "can't sleep", 'tired', 'exhausted', 'fatigue'])) {
      return const MoodSuggestion(emoji: '😴', label: 'Tired', confidence: 0.70);
    }
    if (hasAny(['better', 'relieved', 'proud', 'progress', 'calm', 'good', 'great', 'happy', 'grateful'])) {
      return const MoodSuggestion(emoji: '😊', label: 'Good', confidence: 0.72);
    }

    return const MoodSuggestion(emoji: '🙂', label: 'Neutral', confidence: 0.55);
  }
}
