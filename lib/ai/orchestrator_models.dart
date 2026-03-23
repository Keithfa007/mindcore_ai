import 'agent_action.dart';
import 'agent_type.dart';

class OrchestratorReply {
  final String reply;
  final AgentType agent;
  final double confidence;
  final String supportModeLabel;
  final List<AgentAction> suggestedActions;
  final String ttsText;

  const OrchestratorReply({
    required this.reply,
    required this.agent,
    required this.confidence,
    required this.supportModeLabel,
    required this.suggestedActions,
    required this.ttsText,
  });
}
