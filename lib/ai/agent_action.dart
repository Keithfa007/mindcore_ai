class AgentAction {
  final String type;
  final String label;
  final String? routeName;
  final Map<String, dynamic>? payload;

  const AgentAction({
    required this.type,
    required this.label,
    this.routeName,
    this.payload,
  });

  factory AgentAction.fromJson(Map<String, dynamic> json) {
    return AgentAction(
      type: (json['type'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
      routeName: json['routeName']?.toString(),
      payload: json['payload'] is Map
          ? Map<String, dynamic>.from(json['payload'] as Map)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
        'type': type,
        'label': label,
        if (routeName != null) 'routeName': routeName,
        if (payload != null) 'payload': payload,
      };
}
