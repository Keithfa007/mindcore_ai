class AiBreathingCoachPlan {
  final String label;
  final String inhale;
  final String hold;
  final String exhale;
  final String intro;
  final String outro;

  const AiBreathingCoachPlan({
    required this.label,
    required this.inhale,
    required this.hold,
    required this.exhale,
    required this.intro,
    required this.outro,
  });

  factory AiBreathingCoachPlan.fallback(String moodLabel) {
    final mood = moodLabel.toLowerCase();

    if (mood.contains('panic') || mood.contains('anx')) {
      return const AiBreathingCoachPlan(
        label: 'Nervous system downshift',
        inhale: 'Slow inhale',
        hold: 'Gentle hold',
        exhale: 'Long exhale',
        intro: 'Let the exhale be longer than the inhale. We are telling the body it can slow down now.',
        outro: 'Good. Keep the shoulders soft and let the breath stay unforced.',
      );
    }

    if (mood.contains('tired') || mood.contains('sleep')) {
      return const AiBreathingCoachPlan(
        label: 'Sleep-ready wind down',
        inhale: 'Easy inhale',
        hold: 'Soft hold',
        exhale: 'Long slow exhale',
        intro: 'Ease into a slower rhythm. Nothing to force, just soften and lengthen the exhale.',
        outro: 'Stay with this gentler pace and let your body feel heavier.',
      );
    }

    if (mood.contains('focus') || mood.contains('work')) {
      return const AiBreathingCoachPlan(
        label: 'Calm focus rhythm',
        inhale: 'Steady inhale',
        hold: 'Hold steady',
        exhale: 'Steady exhale',
        intro: 'We will use an even rhythm to steady attention and sharpen focus.',
        outro: 'Nice. Hold onto this steady, capable pace as you continue.',
      );
    }

    return const AiBreathingCoachPlan(
      label: 'Balanced calm rhythm',
      inhale: 'Inhale softly',
      hold: 'Hold gently',
      exhale: 'Exhale slowly',
      intro: 'We are settling into a smooth calming rhythm. Breathe lower and slower.',
      outro: 'Well done. Keep one thread of that calm with you as you move on.',
    );
  }
}

class AiBreathingCoachService {
  static Future<AiBreathingCoachPlan> buildPlan({
    String moodLabel = 'calm',
    String presetName = 'Box',
  }) async {
    final base = AiBreathingCoachPlan.fallback(moodLabel);
    final preset = presetName.toLowerCase();

    if (preset.contains('4-7-8') || preset.contains('478')) {
      return const AiBreathingCoachPlan(
        label: '4-7-8 relaxation rhythm',
        inhale: 'Inhale for four',
        hold: 'Hold for seven',
        exhale: 'Exhale for eight',
        intro: 'We will slow the system with a longer exhale. Keep the breath soft and never forced.',
        outro: 'Beautiful. Let that longer exhale keep softening the body.',
      );
    }

    if (preset.contains('equal')) {
      return const AiBreathingCoachPlan(
        label: 'Equal calm rhythm',
        inhale: 'Inhale evenly',
        hold: 'Hold softly',
        exhale: 'Exhale evenly',
        intro: 'We are using an even rhythm to settle the mind and body.',
        outro: 'Good. Stay with that balanced calm for a few more breaths.',
      );
    }

    return base;
  }

  static AiBreathingCoachPlan recommend({String moodLabel = 'calm'}) {
    return AiBreathingCoachPlan.fallback(moodLabel);
  }
}
