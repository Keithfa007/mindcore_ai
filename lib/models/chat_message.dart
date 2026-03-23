// lib/models/chat_message.dart
import 'package:mindcore_ai/ai/agent_action.dart';

/// Represents a single chat message (user or assistant).
class ChatMessage {
  final String id;
  final String role; // user | assistant
  final String text;
  final DateTime? timestamp;
  final String? routedAgent;
  final String? supportModeLabel;
  final List<AgentAction> suggestedActions;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.text,
    this.timestamp,
    this.routedAgent,
    this.supportModeLabel,
    this.suggestedActions = const [],
  });

  ChatMessage copyWith({
    String? id,
    String? role,
    String? text,
    DateTime? timestamp,
    String? routedAgent,
    String? supportModeLabel,
    List<AgentAction>? suggestedActions,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      text: text ?? this.text,
      timestamp: timestamp ?? this.timestamp,
      routedAgent: routedAgent ?? this.routedAgent,
      supportModeLabel: supportModeLabel ?? this.supportModeLabel,
      suggestedActions: suggestedActions ?? this.suggestedActions,
    );
  }

  factory ChatMessage.fromJson(Map<String, dynamic> j) {
    final rawActions = j['suggestedActions'];
    return ChatMessage(
      id: j['id'] as String,
      role: j['role'] as String,
      text: (j['text'] as String?) ?? '',
      timestamp: j['ts'] != null ? DateTime.tryParse(j['ts'] as String) : null,
      routedAgent: j['routedAgent']?.toString(),
      supportModeLabel: j['supportModeLabel']?.toString(),
      suggestedActions: rawActions is List
          ? rawActions
              .whereType<Map>()
              .map((e) => AgentAction.fromJson(Map<String, dynamic>.from(e)))
              .toList()
          : const [],
    );
  }

  Map<String, dynamic> toJson() {
    final m = <String, dynamic>{
      'id': id,
      'role': role,
      'text': text,
      if (routedAgent != null) 'routedAgent': routedAgent,
      if (supportModeLabel != null) 'supportModeLabel': supportModeLabel,
      if (suggestedActions.isNotEmpty)
        'suggestedActions': suggestedActions.map((a) => a.toJson()).toList(),
    };
    if (timestamp != null) {
      m['ts'] = timestamp!.toIso8601String();
    }
    return m;
  }
}
