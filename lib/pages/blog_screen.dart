// lib/pages/blog_screen.dart
//
// Blog feed — pulls published posts from mindcoreai.eu via WordPress REST API.
// Cached 1 hour. Pull-to-refresh forces a fresh fetch.

import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/blog_service.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/pages/blog_article_screen.dart';

class BlogScreen extends StatefulWidget {
  const BlogScreen({super.key});
  @override
  State<BlogScreen> createState() => _BlogScreenState();
}

class _BlogScreenState extends State<BlogScreen> {
  List<BlogPost> _posts   = [];
  bool _loading           = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool forceRefresh = false}) async {
    setState(() { _loading = true; _error = null; });
    try {
      final posts = await BlogService.getPosts(forceRefresh: forceRefresh);
      if (!mounted) return;
      setState(() {
        _posts   = posts;
        _loading = false;
        if (posts.isEmpty) _error = 'No posts yet. Check back soon.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error   = 'Could not load posts. Check your connection.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Blog'),
      body: AnimatedBackdrop(
        child: RefreshIndicator(
          onRefresh: () => _load(forceRefresh: true),
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? _ErrorState(message: _error!, onRetry: _load)
                  : ListView.separated(
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                      itemCount: _posts.length,
                      separatorBuilder: (_, __) =>
                          const SizedBox(height: 16),
                      itemBuilder: (_, i) => _PostCard(
                        post: _posts[i],
                        isDark: isDark,
                        tt: tt,
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) =>
                                BlogArticleScreen(post: _posts[i]),
                          ),
                        ),
                      ),
                    ),
        ),
      ),
    );
  }
}

// ── Post card ───────────────────────────────────────────────────────────────

class _PostCard extends StatelessWidget {
  final BlogPost post;
  final bool isDark;
  final TextTheme tt;
  final VoidCallback onTap;

  const _PostCard({
    required this.post,
    required this.isDark,
    required this.tt,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: theme.colorScheme.surface,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
              color: theme.dividerColor.withValues(alpha: 0.70)),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.18 : 0.06),
              blurRadius: 16,
              offset: const Offset(0, 4),
            )
          ],
        ),
        clipBehavior: Clip.hardEdge,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Featured image
            if (post.imageUrl != null)
              SizedBox(
                width: double.infinity,
                height: 180,
                child: Image.network(
                  post.imageUrl!,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 180,
                    color: AppColors.primary.withValues(alpha: 0.08),
                    child: Center(
                      child: Icon(Icons.article_rounded,
                          size: 40,
                          color: AppColors.primary.withValues(alpha: 0.35)),
                    ),
                  ),
                ),
              ),

            // No image placeholder strip
            if (post.imageUrl == null)
              Container(
                width: double.infinity,
                height: 6,
                decoration: BoxDecoration(
                  gradient: AppGradients.primaryButton,
                ),
              ),

            Padding(
              padding: const EdgeInsets.all(16),
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
                        letterSpacing: 0.4,
                      ),
                    ),
                  if (post.date.isNotEmpty)
                    const SizedBox(height: 6),

                  // Title
                  Text(
                    post.title,
                    style: tt.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: isDark
                          ? Colors.white
                          : const Color(0xFF0E1320),
                      height: 1.3,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),

                  // Excerpt
                  if (post.excerpt.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      post.excerpt,
                      style: tt.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.55)
                            : const Color(0xFF475467),
                        height: 1.5,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],

                  const SizedBox(height: 12),

                  // Read more
                  Row(
                    children: [
                      Text(
                        'Read article',
                        style: tt.labelSmall?.copyWith(
                          color: AppColors.primary,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Icon(Icons.arrow_forward_rounded,
                          size: 13, color: AppColors.primary),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Error state ───────────────────────────────────────────────────────────────

class _ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorState({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.wifi_off_rounded,
                size: 48,
                color: Colors.white.withValues(alpha: 0.30)),
            const SizedBox(height: 16),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withValues(alpha: 0.55),
                  ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Try again'),
            ),
          ],
        ),
      ),
    );
  }
}
