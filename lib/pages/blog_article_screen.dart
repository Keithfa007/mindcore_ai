// lib/pages/blog_article_screen.dart
//
// Full article reader. Shows the complete post content in-app.
// "Open in browser" button for users who want the full web experience.

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:mindcore_ai/services/blog_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class BlogArticleScreen extends StatelessWidget {
  final BlogPost post;
  const BlogArticleScreen({super.key, required this.post});

  Future<void> _openInBrowser() async {
    final uri = Uri.tryParse(post.link);
    if (uri == null) return;
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs     = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: cs.surface,
      body: AnimatedBackdrop(
        child: CustomScrollView(
          slivers: [
            // ── Collapsible hero header ──────────────────────────────────
            SliverAppBar(
              expandedHeight: post.imageUrl != null ? 240 : 0,
              pinned: true,
              backgroundColor: cs.surface,
              leading: IconButton(
                icon: Icon(Icons.arrow_back_ios_new,
                    color: isDark ? Colors.white : const Color(0xFF0E1320)),
                onPressed: () => Navigator.of(context).pop(),
              ),
              actions: [
                IconButton(
                  icon: Icon(Icons.open_in_browser_rounded,
                      color: AppColors.primary),
                  tooltip: 'Open in browser',
                  onPressed: _openInBrowser,
                ),
              ],
              flexibleSpace: post.imageUrl != null
                  ? FlexibleSpaceBar(
                      background: Image.network(
                        post.imageUrl!,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          color: AppColors.primary.withValues(alpha: 0.10),
                        ),
                      ),
                    )
                  : null,
            ),

            // ── Article content ─────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding:
                    const EdgeInsets.fromLTRB(20, 24, 20, 48),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Date
                    if (post.date.isNotEmpty)
                      Text(
                        post.date,
                        style: tt.labelSmall?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                    if (post.date.isNotEmpty)
                      const SizedBox(height: 10),

                    // Title
                    Text(
                      post.title,
                      style: tt.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                        color: isDark
                            ? Colors.white
                            : const Color(0xFF0E1320),
                        height: 1.25,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Divider
                    Container(
                      height: 2,
                      width: 40,
                      decoration: BoxDecoration(
                        gradient: AppGradients.primaryButton,
                        borderRadius: BorderRadius.circular(1),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Content — render paragraphs
                    ..._buildContent(
                        post.content, tt, isDark),

                    const SizedBox(height: 32),

                    // Open in browser CTA
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: _openInBrowser,
                        icon: const Icon(
                            Icons.open_in_browser_rounded,
                            size: 18),
                        label: const Text('Read on mindcoreai.eu'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(48),
                          side: BorderSide(
                              color: AppColors.primary
                                  .withValues(alpha: 0.50)),
                          shape: RoundedRectangleBorder(
                              borderRadius:
                                  BorderRadius.circular(12)),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  /// Splits the stripped content into paragraphs and renders each.
  List<Widget> _buildContent(
      String content, TextTheme tt, bool isDark) {
    if (content.isEmpty) return [];
    final paragraphs = content
        .split('\n')
        .map((p) => p.trim())
        .where((p) => p.isNotEmpty)
        .toList();

    final widgets = <Widget>[];
    for (final para in paragraphs) {
      widgets.add(Text(
        para,
        style: tt.bodyLarge?.copyWith(
          color: isDark
              ? Colors.white.withValues(alpha: 0.80)
              : const Color(0xFF1A2332),
          height: 1.75,
        ),
      ));
      widgets.add(const SizedBox(height: 16));
    }
    return widgets;
  }
}
