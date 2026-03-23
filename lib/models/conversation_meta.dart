// lib/models/conversation_meta.dart
class ConversationMeta {
  final String id;
  final String title;
  final DateTime updatedAt;
  final String? lastText; // preview of the last message

  ConversationMeta({
    required this.id,
    required this.title,
    DateTime? updatedAt,
    this.lastText,
  }) : updatedAt = updatedAt ?? DateTime.now();

  ConversationMeta copyWith({
    String? id,
    String? title,
    DateTime? updatedAt,
    String? lastText,
  }) {
    return ConversationMeta(
      id: id ?? this.id,
      title: title ?? this.title,
      updatedAt: updatedAt ?? this.updatedAt,
      lastText: lastText ?? this.lastText,
    );
  }

  factory ConversationMeta.fromJson(Map<String, dynamic> j) {
    return ConversationMeta(
      id: j['id'] as String,
      title: (j['title'] as String?)?.trim().isNotEmpty == true
          ? j['title'] as String
          : 'Chat',
      updatedAt: DateTime.tryParse(j['updatedAt'] as String? ?? '') ?? DateTime.now(),
      lastText: j['lastText'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'updatedAt': updatedAt.toIso8601String(),
    if (lastText != null) 'lastText': lastText,
  };
}
