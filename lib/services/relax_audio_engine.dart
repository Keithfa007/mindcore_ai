class RelaxAudioRecommendation {
  final String title;
  final String assetPath;
  final String subtitle;
  final String frequencyLabel;
  final String moodLabel;

  const RelaxAudioRecommendation({
    required this.title,
    required this.assetPath,
    required this.subtitle,
    required this.frequencyLabel,
    required this.moodLabel,
  });
}

class RelaxAudioEngine {
  RelaxAudioEngine._();

  static RelaxAudioRecommendation recommend({
    String moodLabel = 'calm',
  }) {
    final mood = moodLabel.toLowerCase();

    if (mood.contains('panic') || mood.contains('anx') || mood.contains('stress')) {
      return const RelaxAudioRecommendation(
        title: 'Panic Calmer',
        assetPath: 'audio/Panic Calmer.mp3',
        subtitle: 'Slower grounding support for anxious moments.',
        frequencyLabel: '432 Hz calming support',
        moodLabel: 'anxious',
      );
    }

    if (mood.contains('sleep') || mood.contains('tired') || mood.contains('night')) {
      return const RelaxAudioRecommendation(
        title: 'Sleep Transition Session',
        assetPath: 'audio/Sleep Transition Session.mp3',
        subtitle: 'A softer wind-down track for bedtime.',
        frequencyLabel: 'Delta-style wind down',
        moodLabel: 'sleep',
      );
    }

    if (mood.contains('focus') || mood.contains('work') || mood.contains('overwhelm')) {
      return const RelaxAudioRecommendation(
        title: 'Morning Motivation Boost',
        assetPath: 'audio/Morning Motivation Boost.mp3',
        subtitle: 'A steady support track for clearer direction.',
        frequencyLabel: '528 Hz focus support',
        moodLabel: 'focus',
      );
    }

    if (mood.contains('sad') || mood.contains('grief') || mood.contains('low')) {
      return const RelaxAudioRecommendation(
        title: 'Grief Soother',
        assetPath: 'audio/Grief Soother.mp3',
        subtitle: 'Compassionate audio support for heavy emotions.',
        frequencyLabel: '396 Hz grounding support',
        moodLabel: 'sad',
      );
    }

    return const RelaxAudioRecommendation(
      title: 'Calm Breathing Reset',
      assetPath: 'audio/calmbreathingreset.mp3',
      subtitle: 'A balanced reset for general calm.',
      frequencyLabel: '528 Hz gentle reset',
      moodLabel: 'calm',
    );
  }
}
