class ModelRouter {
  static String chooseModel(String message) {
    final lower = message.toLowerCase().trim();

    // Emotional support / short support needs
    if (lower.contains('panic') ||
        lower.contains('anxiety') ||
        lower.contains('stress') ||
        lower.contains('overthinking') ||
        lower.contains('overwhelm')) {
      return 'gpt-4o-mini';
    }

    // More planning / reflective / strategic requests
    if (lower.contains('plan') ||
        lower.contains('strategy') ||
        lower.contains('routine') ||
        lower.contains('long term') ||
        lower.contains('roadmap') ||
        lower.contains('compare')) {
      return 'gpt-4o';
    }

    // Long reflective entries usually benefit from a stronger model
    if (lower.length > 350) {
      return 'gpt-4o';
    }

    return 'gpt-4o-mini';
  }
}
