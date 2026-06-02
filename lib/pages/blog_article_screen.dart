// lib/pages/blog_article_screen.dart
//
// Full article reader. Renders post content with flutter_markdown so
// links are tappable and open in the external browser.

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:mindcore_ai/services/blog_service.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class BlogArticleScreen extends StatelessWidget {
  final BlogPost post;
  const BlogArticleScreen({super.key, required this.post});

  Future<void> _openInBrowser() async {
    final uri = Uri.tryParse(post.link);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _onTapLink(String text, String? href, String title) async {
    if (href == null || href.isEmpty) return;
    final uri = Uri.tryParse(href);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs     = Theme.of(context).colorScheme;

    final textColor   = isDark ? Colors.white.withValues(alpha: 0.85) : const Color(0xFF1A2332);
    final mutedColor  = isDark ? Colors.white.withValues(alpha: 0.50) : const Color(0xFF475467);
    final linkColor   = AppColors.primary;

    // Build a MarkdownStyleSheet that matches the app’s design language
    final mdStyle = MarkdownStyleSheet(
      p: tt.bodyLarge?.copyWith(color: textColor, height: 1.75),
      a: TextStyle(
        color: linkColor,
        decoration: TextDecoration.underline,
        decorationColor: linkColor,
        fontWeight: FontWeight.w600,
      ),
      h1: tt.headlineMedium?.copyWith(color: textColor, fontWeight: FontWeight.w900, height: 1.3),
      h2: tt.headlineSmall?.copyWith(color: textColor, fontWeight: FontWeight.w800, height: 1.3),
      h3: tt.titleLarge?.copyWith(color: textColor, fontWeight: FontWeight.w700, height: 1.4),
      h4: tt.titleMedium?.copyWith(color: textColor, fontWeight: FontWeight.w700),
      strong: TextStyle(color: textColor, fontWeight: FontWeight.w700),
      em: TextStyle(color: textColor, fontStyle: FontStyle.italic),
      blockquote: tt.bodyLarge?.copyWith(
          color: mutedColor, fontStyle: FontStyle.italic, height: 1.7),
      blockquotePadding: const EdgeInsets.only(left: 16),
      blockquoteDecoration: BoxDecoration(
        border: Border(left: BorderSide(color: linkColor.withValues(alpha: 0.50), width: 3)),
      ),
      listBullet: tt.bodyLarge?.copyWith(color: textColor),
      code: tt.bodyMedium?.copyWith(
        fontFamily: 'monospace',
        color: isDark ? const Color(0xFF4CAF82) : const Color(0xFF1B5E20),
        backgroundColor: isDark
            ? Colors.white.withValues(alpha: 0.07)
            : Colors.black.withValues(alpha: 0.05),
      ),
      codeblockDecoration: BoxDecoration(
        color: isDark
            ? Colors.white.withValues(alpha: 0.05)
            : Colors.black.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
      ),
      pPadding: const EdgeInsets.only(bottom: 12),
      h1Padding: const EdgeInsets.only(top: 8, bottom: 8),
      h2Padding: const EdgeInsets.only(top: 8, bottom: 6),
      h3Padding: const EdgeInsets.only(top: 6, bottom: 4),
    );

    return Scaffold(
      backgroundColor: cs.surface,
      body: AnimatedBackdrop(
        child: CustomScrollView(
          slivers: [
            // ── Collapsible hero header ─────────────────────────────────────
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
                  icon: Icon(Icons.open_in_browser_rounded, color: AppColors.primary),
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

            // ── Article content ─────────────────────────────────────────────
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 24, 20, 48),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Date
                    if (post.date.isNotEmpty) ...[
                      Text(
                        post.date,
                        style: tt.labelSmall?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(height: 10),
                    ],

                    // Title
                    Text(
                      post.title,
                      style: tt.headlineSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                        color: isDark ? Colors.white : const Color(0xFF0E1320),
                        height: 1.25,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 20),

                    // Accent divider
                    Container(
                      height: 2, width: 40,
                      decoration: BoxDecoration(
                        gradient: AppGradients.primaryButton,
                        borderRadius: BorderRadius.circular(1),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // Content — rendered as Markdown with tappable links
                    MarkdownBody(
                      data: post.content,
                      styleSheet: mdStyle,
                      onTapLink: _onTapLink,
                      shrinkWrap: true,
                      fitContent: true,
                    ),

                    const SizedBox(height: 32),

                    // Open in browser CTA
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: _openInBrowser,
                        icon: const Icon(Icons.open_in_browser_rounded, size: 18),
                        label: const Text('Read on mindcoreai.eu'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(48),
                          side: BorderSide(
                              color: AppColors.primary.withValues(alpha: 0.50)),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
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
}
