import 'package:mindcore_ai/ai/agent_action.dart';
import 'package:mindcore_ai/ai/agent_type.dart';

class RelaxTrackItem {
  final String id;
  final String title;
  final String subtitle;
  final String assetPath;
  final List<String> tags;

  const RelaxTrackItem({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.assetPath,
    required this.tags,
  });
}

class AudioRecommendationService {
  static const List<RelaxTrackItem> tracks = [
    RelaxTrackItem(
      id: 'body_scan_emotional_tension',
      title: 'Body Scan for Emotional Tension',
      subtitle: 'Release tension gently from head to toe.',
      assetPath: 'audio/Body Scan for Emotional Tension.mp3',
      tags: ['tension', 'body', 'stress', 'release', 'grounding'],
    ),
    RelaxTrackItem(
      id: 'calm_breathing_reset',
      title: 'Calm Breathing Reset',
      subtitle: 'Slow, guided breathing to reset your nervous system.',
      assetPath: 'audio/calmbreathingreset.mp3',
      tags: ['breathing', 'reset', 'calm', 'anxiety', 'panic'],
    ),
    RelaxTrackItem(
      id: 'confidence_grounding',
      title: 'Confidence Grounding',
      subtitle: 'Drop into your body and reconnect with inner strength.',
      assetPath: 'audio/Confidence Grounding.mp3',
      tags: ['confidence', 'grounding', 'prep', 'meeting', 'strength'],
    ),
    RelaxTrackItem(
      id: 'digital_detox_reset',
      title: 'Digital Detox Reset',
      subtitle: 'Step away from screens and clear mental overload.',
      assetPath: 'audio/Digital Detox Reset.mp3',
      tags: ['detox', 'screen', 'overload', 'stress'],
    ),
    RelaxTrackItem(
      id: 'empowering_affirmations',
      title: 'Empowering Affirmations',
      subtitle: 'Positive statements to rebuild self-belief.',
      assetPath: 'audio/Empowering Affirmations.mp3',
      tags: ['affirmations', 'motivation', 'confidence'],
    ),
    RelaxTrackItem(
      id: 'evening_wind_down',
      title: 'Evening Wind Down',
      subtitle: 'Let go of the day and prepare for deep rest.',
      assetPath: 'audio/Evening Wind Down.mp3',
      tags: ['evening', 'night', 'sleep', 'wind down'],
    ),
    RelaxTrackItem(
      id: 'gratitude_moment',
      title: 'Gratitude Moment',
      subtitle: 'Shift into appreciation and calm perspective.',
      assetPath: 'audio/Gratitude Moment.mp3',
      tags: ['gratitude', 'calm', 'perspective'],
    ),
    RelaxTrackItem(
      id: 'grief_soother',
      title: 'Grief Soother',
      subtitle: 'Gentle support for heavy, grieving moments.',
      assetPath: 'audio/Grief Soother.mp3',
      tags: ['grief', 'loss', 'soothing'],
    ),
    RelaxTrackItem(
      id: 'morning_mind_reset',
      title: 'Morning Mind Reset',
      subtitle: 'Start your day clear, calm and focused.',
      assetPath: 'audio/Morning Mind Reset.mp3',
      tags: ['morning', 'reset', 'clarity', 'focus'],
    ),
    RelaxTrackItem(
      id: 'morning_motivation_boost',
      title: 'Morning Motivation Boost',
      subtitle: 'Light a fire under your goals with calm energy.',
      assetPath: 'audio/Morning Motivation Boost.mp3',
      tags: ['morning', 'motivation', 'boost', 'focus'],
    ),
    RelaxTrackItem(
      id: 'overthinking_reset',
      title: 'Overthinking Reset',
      subtitle: 'Step out of your head and back into the present.',
      assetPath: 'audio/Overthinking Reset.mp3',
      tags: ['overthinking', 'worry', 'anxiety', 'mind'],
    ),
    RelaxTrackItem(
      id: 'panic_calmer',
      title: 'Panic Calmer',
      subtitle: 'Short grounding track for intense anxiety spikes.',
      assetPath: 'audio/Panic Calmer.mp3',
      tags: ['panic', 'anxiety', 'grounding', 'urgent'],
    ),
    RelaxTrackItem(
      id: 'reset_after_conflict',
      title: 'Reset After Conflict',
      subtitle: 'Settle your body and mind after arguments or tension.',
      assetPath: 'audio/Reset After Conflict.mp3',
      tags: ['conflict', 'argument', 'tension'],
    ),
    RelaxTrackItem(
      id: 'self_compassion_moment',
      title: 'Self-Compassion Moment',
      subtitle: 'Practice kindness with yourself when you feel low.',
      assetPath: 'audio/Self Compassion Moment.mp3',
      tags: ['self compassion', 'kindness', 'low mood'],
    ),
    RelaxTrackItem(
      id: 'self_compassion',
      title: 'Self-Compassion',
      subtitle: 'Deeper self-compassion practice for emotional healing.',
      assetPath: 'audio/Self Compassion.mp3',
      tags: ['self compassion', 'healing', 'low mood'],
    ),
    RelaxTrackItem(
      id: 'sleep_transition_session',
      title: 'Sleep Transition Session',
      subtitle: 'Drift from alertness into sleep-ready calm.',
      assetPath: 'audio/Sleep Transition Session.mp3',
      tags: ['sleep', 'night', 'rest', 'insomnia'],
    ),
    RelaxTrackItem(
      id: 'social_overwhelm_reset',
      title: 'Social Overwhelm Reset',
      subtitle: 'Come down gently after intense social situations.',
      assetPath: 'audio/Sociall Overwhelm Reset.mp3',
      tags: ['social', 'overwhelm', 'anxiety'],
    ),
    RelaxTrackItem(
      id: 'stress_cleanse',
      title: 'Stress Cleanse',
      subtitle: 'Flush out built-up stress and reboot your system.',
      assetPath: 'audio/Stress Cleanse.mp3',
      tags: ['stress', 'cleanse', 'reset'],
    ),
  ];

  static RelaxTrackItem? byId(String? id) {
    if (id == null || id.trim().isEmpty) return null;
    for (final track in tracks) {
      if (track.id == id) return track;
    }
    return null;
  }

  static RelaxTrackItem recommend({
    required AgentType agent,
    required String userInput,
    required String moodLabel,
  }) {
    final q = userInput.toLowerCase();
    final mood = moodLabel.toLowerCase();

    if (_containsAny(q, const ['panic', 'heart racing', 'shaking', 'can t breathe']) ||
        _containsAny(mood, const ['panic'])) {
      return byId('panic_calmer')!;
    }
    if (_containsAny(q, const ['sleep', 'insomnia', 'night', 'bedtime', 'restless']) ||
        _containsAny(mood, const ['tired', 'exhausted'])) {
      return byId('sleep_transition_session')!;
    }
    if (_containsAny(q, const ['overthinking', 'spiral', 'racing thoughts', 'worry']) ||
        _containsAny(mood, const ['anx', 'overwhelm'])) {
      return byId('overthinking_reset')!;
    }
    if (_containsAny(q, const ['stress', 'tense', 'pressure', 'too much'])) {
      return byId('stress_cleanse')!;
    }
    if (_containsAny(q, const ['meeting', 'appointment', 'conversation', 'before work', 'interview'])) {
      return byId('confidence_grounding')!;
    }
    if (_containsAny(q, const ['focus', 'productive', 'motivation', 'procrastinating'])) {
      return agent == AgentType.routine
          ? byId('morning_motivation_boost')!
          : byId('morning_mind_reset')!;
    }
    if (_containsAny(q, const ['sad', 'low', 'hard on myself', 'guilty'])) {
      return byId('self_compassion_moment')!;
    }
    if (_containsAny(q, const ['argument', 'conflict', 'fight'])) {
      return byId('reset_after_conflict')!;
    }
    if (_containsAny(q, const ['social', 'people', 'crowded'])) {
      return byId('social_overwhelm_reset')!;
    }

    switch (agent) {
      case AgentType.reset:
        return byId('calm_breathing_reset')!;
      case AgentType.sleep:
        return byId('evening_wind_down')!;
      case AgentType.focus:
        return byId('morning_mind_reset')!;
      case AgentType.prep:
        return byId('confidence_grounding')!;
      case AgentType.journalInsight:
        return byId('body_scan_emotional_tension')!;
      case AgentType.routine:
        return byId('morning_motivation_boost')!;
      case AgentType.companion:
        return byId('gratitude_moment')!;
    }
  }

  static AgentAction audioActionFor({
    required AgentType agent,
    required String userInput,
    required String moodLabel,
  }) {
    final track = recommend(agent: agent, userInput: userInput, moodLabel: moodLabel);
    return AgentAction(
      type: 'play_audio',
      label: 'Play ${track.title}',
      routeName: '/relax-audio',
      payload: {
        'trackId': track.id,
        'autoplay': true,
      },
    );
  }

  static bool _containsAny(String text, List<String> needles) {
    for (final needle in needles) {
      if (text.contains(needle)) return true;
    }
    return false;
  }
}
