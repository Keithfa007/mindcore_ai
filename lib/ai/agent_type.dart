enum AgentType {
  companion,
  reset,
  journalInsight,
  routine,
  sleep,
  focus,
  prep,
}

extension AgentTypeX on AgentType {
  String get key {
    switch (this) {
      case AgentType.companion:
        return 'companion';
      case AgentType.reset:
        return 'reset';
      case AgentType.journalInsight:
        return 'journal_insight';
      case AgentType.routine:
        return 'routine';
      case AgentType.sleep:
        return 'sleep';
      case AgentType.focus:
        return 'focus';
      case AgentType.prep:
        return 'prep';
    }
  }

  String get supportModeLabel {
    switch (this) {
      case AgentType.companion:
        return 'Calm Companion';
      case AgentType.reset:
        return 'Calm Reset';
      case AgentType.journalInsight:
        return 'Journal Insight';
      case AgentType.routine:
        return 'Daily Support';
      case AgentType.sleep:
        return 'Sleep Wind-Down';
      case AgentType.focus:
        return 'Focus Reset';
      case AgentType.prep:
        return 'Confidence Prep';
    }
  }

  static AgentType fromKey(String? value) {
    switch (value) {
      case 'reset':
        return AgentType.reset;
      case 'journal_insight':
        return AgentType.journalInsight;
      case 'routine':
        return AgentType.routine;
      case 'sleep':
        return AgentType.sleep;
      case 'focus':
        return AgentType.focus;
      case 'prep':
        return AgentType.prep;
      case 'companion':
      default:
        return AgentType.companion;
    }
  }
}
