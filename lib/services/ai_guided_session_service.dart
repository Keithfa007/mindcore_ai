import 'package:mindcore_ai/services/audio_recommendation_service.dart';

class AiGuidedSessionPlan {
  final String id;
  final String title;
  final String subtitle;
  final String category;
  final String moodHint;
  final int minutes;
  final List<String> steps;
  final String trackId;

  const AiGuidedSessionPlan({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.category,
    required this.moodHint,
    required this.minutes,
    required this.steps,
    required this.trackId,
  });

  RelaxTrackItem? get track => AudioRecommendationService.byId(trackId);
}

class AiGuidedSessionService {
  static const List<AiGuidedSessionPlan> plans = [
    AiGuidedSessionPlan(
      id: 'anxiety_reset',
      title: 'Anxiety Reset',
      subtitle: 'Fast grounding when your body feels tense or overloaded.',
      category: 'Calm now',
      moodHint: 'anxious',
      minutes: 6,
      trackId: 'panic_calmer',
      steps: [
        'Settle your shoulders and unclench your jaw.',
        'Take one slow breath in through the nose.',
        'Lengthen the exhale and soften the chest.',
        'Name one thing you can see and one thing you can feel.',
      ],
    ),
    AiGuidedSessionPlan(
      id: 'sleep_transition',
      title: 'Sleep Transition',
      subtitle: 'Move from mental noise into sleep-ready calm.',
      category: 'Sleep & wind-down',
      moodHint: 'tired',
      minutes: 10,
      trackId: 'sleep_transition_session',
      steps: [
        'Dim stimulation and lower your breathing pace.',
        'Relax the forehead, eyes, jaw, and throat.',
        'Let each exhale become longer than the inhale.',
        'Allow the body to feel heavy and supported.',
      ],
    ),
    AiGuidedSessionPlan(
      id: 'overthinking_reset',
      title: 'Overthinking Reset',
      subtitle: 'Get out of the spiral and back into the present moment.',
      category: 'Calm now',
      moodHint: 'overthinking',
      minutes: 7,
      trackId: 'overthinking_reset',
      steps: [
        'Pause and stop solving for the next few breaths.',
        'Bring attention from the head into the body.',
        'Exhale slowly and let the next thought pass.',
        'Choose one small next action instead of ten.',
      ],
    ),
    AiGuidedSessionPlan(
      id: 'self_compassion',
      title: 'Self-Compassion Moment',
      subtitle: 'A softer session for shame, pressure, or emotional heaviness.',
      category: 'Emotional support',
      moodHint: 'low',
      minutes: 8,
      trackId: 'self_compassion_moment',
      steps: [
        'Notice what feels heavy without pushing it away.',
        'Place a hand on the chest or abdomen.',
        'Use a slower voice with yourself than usual.',
        'Remind yourself that support can begin gently.',
      ],
    ),
    AiGuidedSessionPlan(
      id: 'focus_grounding',
      title: 'Confidence & Focus',
      subtitle: 'Steady your mind before work, calls, or difficult tasks.',
      category: 'Confidence & focus',
      moodHint: 'focused',
      minutes: 5,
      trackId: 'confidence_grounding',
      steps: [
        'Sit taller and breathe lower into the ribs.',
        'Anchor attention on one clear task.',
        'Keep the jaw loose and eyes relaxed.',
        'Move forward with a slower, steadier energy.',
      ],
    ),
  ];

  static List<String> categories() {
    final seen = <String>{};
    final result = <String>[];
    for (final plan in plans) {
      if (seen.add(plan.category)) {
        result.add(plan.category);
      }
    }
    return result;
  }

  static List<AiGuidedSessionPlan> byCategory(String category) {
    return plans.where((p) => p.category == category).toList();
  }

  static AiGuidedSessionPlan recommendForMood(String mood) {
    final q = mood.toLowerCase();
    if (q.contains('sleep') || q.contains('tired') || q.contains('night')) {
      return plans.firstWhere((p) => p.id == 'sleep_transition');
    }
    if (q.contains('low') || q.contains('sad') || q.contains('heavy')) {
      return plans.firstWhere((p) => p.id == 'self_compassion');
    }
    if (q.contains('focus') || q.contains('work') || q.contains('meeting')) {
      return plans.firstWhere((p) => p.id == 'focus_grounding');
    }
    if (q.contains('overthink') || q.contains('spiral') || q.contains('worry')) {
      return plans.firstWhere((p) => p.id == 'overthinking_reset');
    }
    return plans.firstWhere((p) => p.id == 'anxiety_reset');
  }

  static String spokenIntro(AiGuidedSessionPlan plan) {
    return '${plan.title}. ${plan.subtitle} We will take this one step at a time.';
  }
}
