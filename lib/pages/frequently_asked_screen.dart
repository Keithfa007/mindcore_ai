// Frequently Asked — Theme-first UI using PageScaffold + GlassCard (Dart 2.x)
// Location: lib/pages/frequently_asked_screen.dart

import 'package:flutter/material.dart';
import '../data/frequently_asked.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/glass_card.dart';
import 'theme_questions_screen.dart';

/// Compat alias for your nav helpers (const constructor)
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
  String _query = ""; // filters theme titles

  List<QATheme> get _themesSorted {
    final list = List<QATheme>.from(frequentlyAskedData);
    list.sort((a, b) => a.title.toLowerCase().compareTo(b.title.toLowerCase()));
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
    final theme = Theme.of(context);

    return PageScaffold(
      title: 'Frequently Asked',
      bottomIndex: 7,
      body: Column(
        children: [
          // Search themes
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
              ],
            ),
          ),

          const Divider(height: 1),

          // Theme tiles
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 24),
              itemCount: _themesSorted.length,
              itemBuilder: (context, index) {
                final t = _themesSorted[index];
                return _ThemeTile(
                  title: t.title,
                  count: t.items.length,
                  onTap: () => _openTheme(t),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _ThemeTile extends StatelessWidget {
  final String title;
  final int count;
  final VoidCallback onTap;

  const _ThemeTile({
    Key? key,
    required this.title,
    required this.count,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: GlassCard(
        padding: const EdgeInsets.fromLTRB(14, 10, 12, 10),
        child: ListTile(
          onTap: onTap,
          contentPadding: EdgeInsets.zero,
          title: Text(
            title,
            style:
            theme.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
          subtitle: Text('$count questions'),
          trailing: const Icon(Icons.chevron_right),
        ),
      ),
    );
  }
}
