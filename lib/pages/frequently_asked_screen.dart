// lib/pages/frequently_asked_screen.dart
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

import '../data/frequently_asked.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/glass_card.dart';
import 'theme_questions_screen.dart';

/// Compat alias
class FrequentlyAskedScreen extends StatelessWidget {
  const FrequentlyAskedScreen({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) => const FrequentlyAskedPage();
}

class FrequentlyAskedPage extends StatefulWidget {
  const FrequentlyAskedPage({Key? key}) : super(key: key);
  @override
  State<FrequentlyAskedPage> createState() => _FrequentlyAskedPageState();
}

class _FrequentlyAskedPageState extends State<FrequentlyAskedPage> {
  String _query = '';
  bool   _isLoadingRemote = true;

  // Remote new themes from Firestore (faq_themes collection)
  List<QATheme>     _remoteThemes    = [];
  Set<String>       _newThemeTitles  = {};

  // Extra questions for existing local themes (faq_extra_questions collection)
  Map<String, List<QA>> _extraQuestionsMap = {};

  @override
  void initState() {
    super.initState();
    _loadFromFirestore();
  }

  // ── Firestore loading ─────────────────────────────────────────────────────────
  Future<void> _loadFromFirestore() async {
    try {
      // 1. Load new themes
      final themesSnapshot = await FirebaseFirestore.instance
          .collection('faq_themes')
          .get();

      final remoteThemes   = <QATheme>[];
      final newTitles      = <String>{};

      var idCounter = 10000;
      for (final doc in themesSnapshot.docs) {
        final d = doc.data();
        if (d['active'] != true) continue;

        final title = d['title']?.toString() ?? '';
        if (d['is_new'] == true) newTitles.add(title);

        final rawItems = d['items'] as List? ?? [];
        final items = rawItems.asMap().entries.map((entry) {
          final item = entry.value as Map<String, dynamic>;
          return QA(
            id:       idCounter++,
            question: item['question']?.toString() ?? '',
            answer:   item['answer']?.toString()   ?? '',
          );
        }).toList();

        remoteThemes.add(QATheme(title: title, items: items));
      }

      // Sort remote themes newest first (Firestore docs don't have guaranteed order
      // so we just keep them as returned — pipeline always puts newest first)
      remoteThemes.sort((a, b) => a.title.compareTo(b.title));

      // 2. Load extra questions for existing themes
      final extraSnapshot = await FirebaseFirestore.instance
          .collection('faq_extra_questions')
          .get();

      final extraMap = <String, List<QA>>{};
      for (final doc in extraSnapshot.docs) {
        final d          = doc.data();
        final themeTitle = d['theme_title']?.toString() ?? '';
        if (themeTitle.isEmpty) continue;

        final rawItems = d['extra_items'] as List? ?? [];
        final items = rawItems.asMap().entries.map((entry) {
          final item = entry.value as Map<String, dynamic>;
          return QA(
            id:       20000 + idCounter++,
            question: item['question']?.toString() ?? '',
            answer:   item['answer']?.toString()   ?? '',
          );
        }).toList();

        // Append if theme already has extra items
        extraMap[themeTitle] = [...(extraMap[themeTitle] ?? []), ...items];
      }

      if (kDebugMode) {
        debugPrint('FAQ: ${remoteThemes.length} remote theme(s), '
            '${extraMap.length} theme(s) with extra questions');
      }

      if (!mounted) return;
      setState(() {
        _remoteThemes       = remoteThemes;
        _newThemeTitles     = newTitles;
        _extraQuestionsMap  = extraMap;
        _isLoadingRemote    = false;
      });
    } catch (e) {
      if (kDebugMode) debugPrint('FAQ Firestore error: $e');
      if (!mounted) return;
      setState(() => _isLoadingRemote = false);
    }
  }

  // ── Combined + filtered theme list ────────────────────────────────────────────
  List<QATheme> get _allThemes {
    // Merge extra questions into local themes
    final localWithExtras = frequentlyAskedData.map((theme) {
      final extra = _extraQuestionsMap[theme.title] ?? [];
      if (extra.isEmpty) return theme;
      return QATheme(title: theme.title, items: [...theme.items, ...extra]);
    }).toList();

    // Remote new themes first, then local
    return [..._remoteThemes, ...localWithExtras];
  }

  List<QATheme> get _themesSorted {
    final list = List<QATheme>.from(_allThemes);
    if (_query.trim().isEmpty) return list;
    final q = _query.toLowerCase();
    return list.where((t) => t.title.toLowerCase().contains(q)).toList();
  }

  void _openTheme(QATheme t) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ThemeQuestionsPage(title: t.title, items: t.items),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme   = Theme.of(context);
    final cs      = theme.colorScheme;
    final themes  = _themesSorted;

    return PageScaffold(
      title: 'Frequently Asked',
      bottomIndex: 7,
      body: Column(
        children: [
          // Search
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: TextField(
              onChanged: (v) => setState(() => _query = v),
              decoration: const InputDecoration(
                hintText: 'Search…',
                prefixIcon: Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.all(Radius.circular(12)),
                ),
              ),
            ),
          ),

          // Subheader
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 6),
            child: Row(
              children: [
                Text('Themes (A–Z)', style: theme.textTheme.labelLarge),
                const Spacer(),
                if (_isLoadingRemote)
                  SizedBox(
                    width: 14, height: 14,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.5, color: cs.primary,
                    ),
                  ),
              ],
            ),
          ),

          const Divider(height: 1),

          // Theme tiles
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 24),
              itemCount: themes.length,
              itemBuilder: (context, index) {
                final t     = themes[index];
                final isNew = _newThemeTitles.contains(t.title);
                return _ThemeTile(
                  title:  t.title,
                  count:  t.items.length,
                  isNew:  isNew,
                  onTap:  () => _openTheme(t),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ── Theme tile ────────────────────────────────────────────────────────────────
class _ThemeTile extends StatelessWidget {
  final String   title;
  final int      count;
  final bool     isNew;
  final VoidCallback onTap;

  const _ThemeTile({
    Key? key,
    required this.title,
    required this.count,
    required this.isNew,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs    = theme.colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: GlassCard(
        padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
        child: ListTile(
          onTap: onTap,
          contentPadding: EdgeInsets.zero,
          title: Row(
            children: [
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              if (isNew) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.tealAccent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    'New',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: Colors.teal, fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ],
          ),
          subtitle: Text('$count questions'),
          trailing: const Icon(Icons.chevron_right),
        ),
      ),
    );
  }
}
