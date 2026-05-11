class LearningTopic {
  final String id;              // stable slug
  final String title;
  final String overview;
  final List<String> examples;
  final List<String> strategies;
  final List<String> tags;
  final bool isFavorite;
  final bool isNew;
  final DateTime createdAt;
  final DateTime updatedAt;

  LearningTopic({
    required this.id,
    required this.title,
    required this.overview,
    required this.examples,
    required this.strategies,
    this.tags = const [],
    bool? isFavorite,
    bool? isNew,
    DateTime? createdAt,
    DateTime? updatedAt,
  })  : isFavorite = isFavorite ?? false,
        isNew = isNew ?? false,
        createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();

  LearningTopic copyWith({
    String? title,
    String? overview,
    List<String>? examples,
    List<String>? strategies,
    List<String>? tags,
    bool? isFavorite,
    bool? isNew,
    DateTime? updatedAt,
  }) {
    return LearningTopic(
      id: id,
      title: title ?? this.title,
      overview: overview ?? this.overview,
      examples: examples ?? this.examples,
      strategies: strategies ?? this.strategies,
      tags: tags ?? this.tags,
      isFavorite: isFavorite ?? this.isFavorite,
      isNew: isNew ?? this.isNew,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }

  factory LearningTopic.fromJson(Map<String, dynamic> j) => LearningTopic(
    id: (j['id'] ?? '').toString(),
    title: (j['title'] ?? '').toString(),
    overview: (j['overview'] ?? '').toString(),
    examples: (j['examples'] as List?)?.map((e) => e.toString()).toList() ?? const [],
    strategies: (j['strategies'] as List?)?.map((e) => e.toString()).toList() ?? const [],
    tags: (j['tags'] as List?)?.map((e) => e.toString()).toList() ?? const [],
    isFavorite: (j['fav'] as bool?) ?? false,
    isNew: (j['isNew'] as bool?) ?? false,
    createdAt: DateTime.tryParse((j['createdAt'] ?? '') as String? ?? '') ?? DateTime.now(),
    updatedAt: DateTime.tryParse((j['updatedAt'] ?? '') as String? ?? '') ?? DateTime.now(),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'overview': overview,
    'examples': examples,
    'strategies': strategies,
    'tags': tags,
    'fav': isFavorite,
    'isNew': isNew,
    'createdAt': createdAt.toIso8601String(),
    'updatedAt': updatedAt.toIso8601String(),
  };
}
