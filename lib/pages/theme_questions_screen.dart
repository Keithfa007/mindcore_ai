// Theme Questions Page — full-screen per theme with PageScaffold + GlassCard
// Location: lib/pages/theme_questions_page.dart

import 'package:flutter/material.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/glass_card.dart';
import '../data/frequently_asked.dart';

class ThemeQuestionsPage extends StatefulWidget {
  final String title;
  final List<QA> items;

  const ThemeQuestionsPage({
    Key? key,
    required this.title,
    required this.items,
  }) : super(key: key);

  @override
  State<ThemeQuestionsPage> createState() => _ThemeQuestionsPageState();
}

class _ThemeQuestionsPageState extends State<ThemeQuestionsPage> {
  String _query = "";

  List<QA> get _filtered {
    if (_query.trim().isEmpty) return widget.items;
    final q = _query.toLowerCase();
    return widget.items.where((qa) =>
    qa.question.toLowerCase().contains(q) ||
        qa.answer.toLowerCase().contains(q)
    ).toList();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PageScaffold(
      title: widget.title,
      bottomIndex: 0, // show bottom nav; set to the tab you want highlighted
      body: Column(
        children: [
          // Search within theme
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
                Text(
                  _query.isEmpty ? 'All questions' : 'Results for "$_query"',
                  style: theme.textTheme.labelLarge,
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Q&A list
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 6, 12, 24),
              itemCount: _filtered.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final qa = _filtered[i];
                return GlassCard(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Theme(
                    data: Theme.of(context).copyWith(
                      dividerColor: Colors.transparent,
                    ),
                    child: ExpansionTile(
                      tilePadding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      title: Text(
                        qa.question,
                        style: theme.textTheme.bodyLarge
                            ?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      children: [
                        Padding(
                          padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                          child: SelectableText(
                            qa.answer,
                            style: theme.textTheme.bodyMedium,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
