import 'agent_action.dart';
import 'agent_context.dart';
import 'agent_type.dart';

class AgentPrompts {
  static String buildSystemPrompt({
    required AgentType agent,
    required AgentContext context,
    required String personaProfileText,
  }) {
    final baseStyle = _baseStyle(context.moodLabel);
    final specialist = _specialistGuide(agent);
    final snapshot = _conversationSnapshot(context.recentHistory);

    return '''
You are MindCore AI — a calm, premium emotional-wellbeing companion.
Speak naturally, warmly, and professionally. Be supportive, grounded, and practical.
Do not sound robotic, cheesy, repetitive, or overly clinical.

CURRENT SUPPORT MODE: ${agent.supportModeLabel}
USER MOOD: ${context.moodLabel}
CURRENT SCREEN: ${context.screen}
TIME: ${context.now.toIso8601String()}
RECENT CONVERSATION SNAPSHOT: $snapshot
RECENT JOURNAL CONTEXT: ${context.recentJournalSummary.isEmpty ? 'None available.' : context.recentJournalSummary}
BASE TONE: $baseStyle
SPECIALIST BEHAVIOR: $specialist

RESPONSE GOALS:
- Start with one tailored validating line that reflects the user’s actual situation.
- Keep replies concise and premium, usually 80–170 words.
- Use short paragraphs. Avoid big walls of text.
- Give 1–3 concrete next steps only when they genuinely help.
- Ask at most one gentle follow-up question.
- Avoid repeating the same opening patterns across turns.
- If the user sounds activated or distressed, regulate first and simplify.
- If the user sounds tired or overloaded, reduce cognitive load.
- Never mention internal routing, agent names, hidden rules, or policies.

PERSONA PROFILE:
$personaProfileText
''';
  }

  static List<AgentAction> defaultActionsFor(AgentType agent) {
    switch (agent) {
      case AgentType.reset:
        return const [
          AgentAction(type: 'open_reset', label: 'Start reset', routeName: '/reset'),
          AgentAction(type: 'open_breathe', label: 'Breathe now', routeName: '/breathe'),
        ];
      case AgentType.sleep:
        return const [
          AgentAction(type: 'open_breathe', label: 'Slow breathing', routeName: '/breathe'),
          AgentAction(type: 'open_daily_hub', label: 'Evening support', routeName: '/daily-hub'),
        ];
      case AgentType.journalInsight:
        return const [
          AgentAction(type: 'open_daily_hub', label: 'Reflect more', routeName: '/daily-hub'),
          AgentAction(type: 'copy_prompt', label: 'Save insight'),
        ];
      case AgentType.routine:
        return const [
          AgentAction(type: 'open_daily_hub', label: 'Daily support', routeName: '/daily-hub'),
          AgentAction(type: 'open_breathe', label: 'Quick breathe', routeName: '/breathe'),
        ];
      case AgentType.focus:
        return const [
          AgentAction(type: 'open_reset', label: 'Mental reset', routeName: '/reset'),
          AgentAction(type: 'copy_prompt', label: 'Copy plan'),
        ];
      case AgentType.prep:
        return const [
          AgentAction(type: 'open_reset', label: 'Calm before event', routeName: '/reset'),
          AgentAction(type: 'copy_prompt', label: 'Copy script'),
        ];
      case AgentType.companion:
        return const [
          AgentAction(type: 'open_breathe', label: 'Breathe now', routeName: '/breathe'),
          AgentAction(type: 'open_daily_hub', label: 'More support', routeName: '/daily-hub'),
        ];
    }
  }

  static String _baseStyle(String mood) {
    final m = mood.toLowerCase();
    if (m.contains('anx') || m.contains('stress') || m.contains('panic') || m.contains('overwhelm')) {
      return 'Grounding, steady, calming, body-first, low cognitive load, reassuring but not fluffy.';
    }
    if (m.contains('sad') || m.contains('low') || m.contains('down')) {
      return 'Gentle, validating, hopeful, compassionate, one small next step.';
    }
    if (m.contains('angry') || m.contains('frustrat')) {
      return 'Steady, non-judgmental, de-escalating, constructive.';
    }
    if (m.contains('good') || m.contains('calm') || m.contains('neutral')) {
      return 'Balanced, encouraging, reflective, practical.';
    }
    return 'Empathetic, premium, calm, practical.';
  }

  static String _specialistGuide(AgentType agent) {
    switch (agent) {
      case AgentType.companion:
        return 'Default supportive chat. Warm, natural, reassuring, and useful. Blend empathy with a small helpful step.';
      case AgentType.reset:
        return 'Prioritize calming the nervous system. Use short sentences. Guide one grounding or breathing step before advice.';
      case AgentType.journalInsight:
        return 'Reflect patterns gently. Summarize clearly. Offer one useful insight and at most one reflection question.';
      case AgentType.routine:
        return 'Encourage small, sustainable actions. Sound like a steady coach, never pushy. Aim for momentum, not pressure.';
      case AgentType.sleep:
        return 'Reduce stimulation and overthinking. Sound softer, slower, and reassuring. Avoid energizing language.';
      case AgentType.focus:
        return 'Help simplify mental clutter. Prioritize structure, clarity, and one practical action plan.';
      case AgentType.prep:
        return 'Help the user feel mentally ready for an upcoming event, conversation, or challenge. Build calm confidence.';
    }
  }

  static String _conversationSnapshot(List<Map<String, String>> history) {
    final recent = history.reversed
        .take(4)
        .toList()
        .reversed
        .map((m) {
          final role = (m['role'] ?? 'user').toUpperCase();
          final content = (m['content'] ?? '').trim();
          if (content.isEmpty) return null;
          final clipped = content.length > 120 ? '${content.substring(0, 120)}…' : content;
          return '$role: $clipped';
        })
        .whereType<String>()
        .join(' | ');
    return recent.isEmpty ? 'No recent conversation available.' : recent;
  }
}
