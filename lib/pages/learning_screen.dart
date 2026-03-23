import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/learning_repo.dart';
import 'package:mindcore_ai/models/learning_topic.dart';

// Shared UI
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

class LearningScreen extends StatefulWidget {
  const LearningScreen({super.key});
  @override
  State<LearningScreen> createState() => _LearningScreenState();
}

class _LearningScreenState extends State<LearningScreen> {
  List<LearningTopic> _all = [];
  List<LearningTopic> _filtered = [];
  bool _loading = true;
  String _query = '';
  bool _showFavOnly = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final list = await LearningRepo.load();
    if (!mounted) return;
    setState(() {
      _all = list;
      _applyFilter();
      _loading = false;
    });
  }

  void _applyFilter() {
    final q = _query.trim().toLowerCase();
    Iterable<LearningTopic> list = _all;
    if (_showFavOnly) list = list.where((t) => t.isFavorite);
    if (q.isNotEmpty) {
      list = list.where((t) =>
      t.title.toLowerCase().contains(q) ||
          t.overview.toLowerCase().contains(q) ||
          t.tags.any((x) => x.toLowerCase().contains(q)));
    }
    _filtered = list.toList()
      ..sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
  }

  Future<void> _toggleFav(LearningTopic t) async {
    await LearningRepo.setFavorite(t.id, !t.isFavorite);
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    // Make the pinned header tall enough for larger text scales.
    // Base ~232 plus extra growth with textScale; clamped for sanity.
    final ts = MediaQuery.textScalerOf(context).scale(1.0);
    final double headerHeight = 232 + (ts - 1.0) * 120; // was ~190; this prevents overflows

    return PageScaffold(
      title: 'Learning',
      bottomIndex: 3,
      body: AnimatedBackdrop(
        child: RefreshIndicator(
          onRefresh: _load,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              // Pinned top: hero + search/filters
              SliverAppBar(
                pinned: true,
                backgroundColor: Colors.transparent,
                elevation: 0,
                collapsedHeight: headerHeight,
                expandedHeight: headerHeight,
                automaticallyImplyLeading: false,
                flexibleSpace: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),
                  child: GlassCard(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const SectionHeroCard(
                            title: 'Mental health library',
                            subtitle:
                            'Tap a topic to read: overview • examples • what can be done',
                          ),
                          const SizedBox(height: 10),
                          _toolbar(),
                        ],
                      ),
                    ),
                  ),
                ),
              ),

              // Content
              if (_loading)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(12, 12, 12, 24),
                    child: ListTile(title: Text('Loading topics…')),
                  ),
                )
              else if (_filtered.isEmpty)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(12, 12, 12, 24),
                    child: _EmptyState(),
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(0, 8, 0, 24),
                  sliver: SliverList(
                    delegate: SliverChildBuilderDelegate(
                          (ctx, i) => _topicTile(_filtered[i]),
                      childCount: _filtered.length,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _toolbar() {
    return Row(
      children: [
        Expanded(
          child: TextField(
            decoration: const InputDecoration(
              hintText: 'Search topics…',
              prefixIcon: Icon(Icons.search),
              border: OutlineInputBorder(
                borderSide: BorderSide.none,
                borderRadius: BorderRadius.all(Radius.circular(12)),
              ),
              filled: true,
            ),
            onChanged: (v) {
              setState(() {
                _query = v;
                _applyFilter();
              });
            },
          ),
        ),
        const SizedBox(width: 8),
        FilterChip(
          label: const Text('Favorites'),
          selected: _showFavOnly,
          onSelected: (v) => setState(() {
            _showFavOnly = v;
            _applyFilter();
          }),
        ),
      ],
    );
  }

  Widget _topicTile(LearningTopic t) {
    final subtitle = _short(t.overview, max: 120);
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 10),
      child: GlassCard(
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 12),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
          title: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: _SeedHeader(title: t.title, subtitle: subtitle)),
              IconButton(
                tooltip: t.isFavorite ? 'Unfavorite' : 'Favorite',
                onPressed: () => _toggleFav(t),
                icon: Icon(t.isFavorite ? Icons.favorite : Icons.favorite_border),
              ),
            ],
          ),
          children: [
            const Divider(),
            _sectionHeader('Overview'),
            _para(t.overview),
            const SizedBox(height: 8),
            _sectionHeader('Common examples'),
            _bullets(t.examples),
            const SizedBox(height: 8),
            _sectionHeader('What can be done'),
            _bullets(t.strategies),
          ],
        ),
      ),
    );
  }

  String _short(String s, {int max = 100}) {
    final v = s.trim();
    if (v.length <= max) return v;
    return '${v.substring(0, max).trimRight()}…';
  }

  Widget _sectionHeader(String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(text, style: const TextStyle(fontWeight: FontWeight.w700)),
    );
  }

  Widget _para(String text) {
    return Text(text, style: const TextStyle(height: 1.35));
  }

  Widget _bullets(List<String> items) {
    if (items.isEmpty) return const Text('—');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: items
          .map(
            (e) => Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('• '),
              Expanded(child: Text(e)),
            ],
          ),
        ),
      )
          .toList(),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 24, 12, 24),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        boxShadow: const [
          BoxShadow(color: Color(0x14000000), blurRadius: 8, offset: Offset(0, 2))
        ],
      ),
      child: const Center(
        child: Text('No topics found. Adjust your filters or add more seeds.'),
      ),
    );
  }
}

/// Smaller header used inside each seed card (title a bit smaller than the hero)
class _SeedHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  const _SeedHeader({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: (t.titleMedium ?? const TextStyle())
              .copyWith(fontWeight: FontWeight.w800, fontSize: 18, height: 1.1),
        ),
        const SizedBox(height: 2),
        Text(
          subtitle,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: (t.bodyMedium ?? const TextStyle())
              .copyWith(color: const Color(0xFF334155), height: 1.25),
        ),
      ],
    );
  }
}
