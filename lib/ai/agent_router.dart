import 'agent_context.dart';
import 'agent_decision.dart';
import 'agent_prompts.dart';
import 'agent_type.dart';

class AgentRouter {
  static AgentDecision decide(AgentContext context) {
    final q = _normalize(context.userInput);
    final mood = _normalize(context.moodLabel);
    final screen = _normalize(context.screen);
    final history = _normalize(context.recentUserText);
    final journal = _normalize(context.recentJournalSummary);

    double reset = 0.0;
    double journalInsight = 0.0;
    double routine = 0.0;
    double sleep = 0.0;
    double focus = 0.0;
    double prep = 0.0;
    double companion = 0.34;

    if (_containsAny(q, const [
      'panic', 'overwhelmed', 'overwhelm', 'spiral', 'too much', 'cant cope',
      'can t cope', 'anxious', 'anxiety', 'heart racing', 'cant breathe',
      'can t breathe', 'stressed', 'stress', 'shaking', 'meltdown'
    ])) {
      reset += 0.62;
    }
    if (_containsAny(mood, const ['anx', 'stress', 'panic', 'overwhelm'])) {
      reset += 0.24;
    }
    if (_containsAny(history, const ['panic', 'anxious', 'stress', 'spiral'])) {
      reset += 0.18;
    }

    if (_containsAny(screen, const ['journal']) ||
        _containsAny(q, const [
          'journal', 'reflect', 'pattern', 'why do i keep', 'why am i',
          'make sense of', 'understand this', 'insight', 'summarise', 'summarize'
        ]) ||
        (context.recentJournalSummary.isNotEmpty && q.length > 100)) {
      journalInsight += 0.58;
    }
    if (_containsAny(journal, const ['feel', 'feeling', 'stress', 'relationship', 'tired', 'sleep'])) {
      journalInsight += 0.10;
    }

    if (_containsAny(q, const [
      'sleep', 'insomnia', 'bedtime', 'cant sleep', 'can t sleep', 'switch off',
      'racing thoughts at night', 'wake up', 'keep waking', 'restless'
    ])) {
      sleep += 0.68;
    }
    if (context.isEvening && _containsAny(q, const ['anxious', 'worry', 'racing thoughts', 'restless', 'tense'])) {
      sleep += 0.24;
    }
    if (context.isEvening && _containsAny(history, const ['sleep', 'tired', 'exhausted'])) {
      sleep += 0.14;
    }

    if (_containsAny(q, const [
      'focus', 'concentrate', 'productive', 'procrastinating', 'procrastinate',
      'scattered', 'work stress', 'cluttered', 'cant focus', 'can t focus',
      'too many things', 'unproductive', 'stuck'
    ])) {
      focus += 0.62;
    }
    if (_containsAny(history, const ['work', 'deadline', 'focus', 'productive', 'overthinking'])) {
      focus += 0.16;
    }

    if (_containsAny(q, const [
      'tomorrow', 'meeting', 'appointment', 'conversation', 'before i go',
      'before work', 'before my', 'what should i say', 'how do i prepare',
      'later today', 'interview', 'visit', 'event'
    ])) {
      prep += 0.60;
    }

    if (_containsAny(q, const [
      'goal', 'routine', 'habit', 'morning', 'motivation', 'today plan',
      'streak', 'check in', 'check-in', 'start my day', 'daily plan'
    ])) {
      routine += 0.60;
    }
    if (context.isMorning && q.length < 130) {
      routine += 0.16;
    }

    if (_containsAny(q, const ['thank you', 'thanks', 'okay', 'ok', 'i see', 'that helps'])) {
      companion += 0.12;
    }
    if (q.split(' ').length <= 8 &&
        !_containsAny(q, const ['sleep', 'focus', 'meeting', 'panic', 'journal', 'routine'])) {
      companion += 0.10;
    }

    final scores = <AgentType, double>{
      AgentType.companion: companion,
      AgentType.reset: reset,
      AgentType.journalInsight: journalInsight,
      AgentType.routine: routine,
      AgentType.sleep: sleep,
      AgentType.focus: focus,
      AgentType.prep: prep,
    };

    final ordered = scores.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    final best = ordered.first;
    final second = ordered.length > 1 ? ordered[1] : ordered.first;

    final reason = _reasonFor(best.key, second.key, context);
    final confidence = _confidence(best.value, second.value);

    return AgentDecision(
      agent: best.key,
      confidence: confidence,
      reason: reason,
      actions: AgentPrompts.defaultActionsFor(best.key),
    );
  }

  static String _normalize(String value) => value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9\s]'), ' ');

  static bool _containsAny(String text, List<String> needles) {
    for (final n in needles) {
      if (text.contains(n)) return true;
    }
    return false;
  }

  static double _confidence(double best, double second) {
    final margin = (best - second).clamp(0.0, 0.35);
    return (0.52 + best * 0.35 + margin).clamp(0.40, 0.98);
  }

  static String _reasonFor(AgentType best, AgentType second, AgentContext context) {
    final alt = second == best ? '' : ' Secondary pull: ${second.supportModeLabel}.';
    return 'Primary match from message intent, mood, recent user turns, and time of day.${context.recentJournalSummary.isNotEmpty ? ' Journal context included.' : ''}$alt';
  }
}
