class ProactiveSuggestions {
  static List<String> suggestions(String userMessage) {
    final msg = userMessage.toLowerCase();

    if (msg.contains('stress') ||
        msg.contains('anxiety') ||
        msg.contains('overthinking') ||
        msg.contains('panic')) {
      return [
        'Try a 60-second breathing reset',
        'Write a quick reflection',
        'Listen to a calming audio'
      ];
    }

    if (msg.contains('sleep') ||
        msg.contains('tired') ||
        msg.contains('insomnia')) {
      return [
        'Start a wind-down breathing session',
        'Read tonight\'s affirmation',
        'Play relaxing background audio'
      ];
    }

    if (msg.contains('motivation') ||
        msg.contains('focus') ||
        msg.contains('discipline')) {
      return [
        'Set one small goal for today',
        'Read today\'s affirmation',
        'Do a 2-minute reset'
      ];
    }

    return [
      'Reflect in your journal',
      'Read today\'s affirmation',
      'Do a quick breathing exercise'
    ];
  }
}
