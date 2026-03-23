class AgentContext {
  final String userInput;
  final String moodLabel;
  final String screen;
  final List<Map<String, String>> recentHistory;
  final String recentJournalSummary;
  final DateTime now;

  const AgentContext({
    required this.userInput,
    required this.moodLabel,
    required this.screen,
    required this.recentHistory,
    required this.recentJournalSummary,
    required this.now,
  });

  bool get isEvening => now.hour >= 20 || now.hour < 5;
  bool get isMorning => now.hour >= 5 && now.hour < 11;

  Iterable<Map<String, String>> get recentUserTurns =>
      recentHistory.where((m) => (m['role'] ?? '').toLowerCase() == 'user');

  String get recentUserText => recentUserTurns
      .map((m) => (m['content'] ?? '').trim())
      .where((t) => t.isNotEmpty)
      .join(' ');
}
