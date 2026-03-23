import 'agent_action.dart';
import 'agent_type.dart';

class AgentDecision {
  final AgentType agent;
  final double confidence;
  final String reason;
  final List<AgentAction> actions;

  const AgentDecision({
    required this.agent,
    required this.confidence,
    required this.reason,
    required this.actions,
  });
}
