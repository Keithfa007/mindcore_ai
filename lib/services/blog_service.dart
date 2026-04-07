// lib/services/blog_service.dart
//
// Fetches published posts from mindcoreai.eu via the WordPress REST API.
// Caches responses for 1 hour so the screen loads instantly on repeat visits.
// Falls back to cached data if the network is unavailable.

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class BlogPost {
  final int    id;
  final String title;
  final String excerpt;   // plain text, HTML stripped
  final String content;   // plain text, HTML stripped
  final String date;      // formatted: "7 April 2026"
  final String link;      // canonical URL on mindcoreai.eu
  final String? imageUrl; // featured image, may be null

  const BlogPost({
    required this.id,
    required this.title,
    required this.excerpt,
    required this.content,
    required this.date,
    required this.link,
    this.imageUrl,
  });

  Map<String, dynamic> toJson() => {
        'id':       id,
        'title':    title,
        'excerpt':  excerpt,
        'content':  content,
        'date':     date,
        'link':     link,
        'imageUrl': imageUrl,
      };

  factory BlogPost.fromJson(Map<String, dynamic> j) => BlogPost(
        id:       (j['id'] as int?    ) ?? 0,
        title:    (j['title']    as String?) ?? '',
        excerpt:  (j['excerpt']  as String?) ?? '',
        content:  (j['content']  as String?) ?? '',
        date:     (j['date']     as String?) ?? '',
        link:     (j['link']     as String?) ?? '',
        imageUrl: j['imageUrl']  as String?,
      );
}

class BlogService {
  static const _endpoint =
      'https://mindcoreai.eu/wp-json/wp/v2/posts'
      '?_embed&per_page=20&orderby=date&order=desc&status=publish';

  static const _kCache     = 'blog_posts_v1';
  static const _kCacheTime = 'blog_posts_time_v1';
  static const _cacheTtlMs = 60 * 60 * 1000; // 1 hour

  // ── Public API ─────────────────────────────────────────────────────

  static Future<List<BlogPost>> getPosts({bool forceRefresh = false}) async {
    final prefs = await SharedPreferences.getInstance();

    if (!forceRefresh) {
      final cached = _loadCache(prefs);
      if (cached != null) return cached;
    }

    try {
      final response = await http
          .get(Uri.parse(_endpoint))
          .timeout(const Duration(seconds: 12));

      if (response.statusCode != 200) {
        return _loadCache(prefs) ?? [];
      }

      final raw     = jsonDecode(response.body) as List;
      final posts   = raw
          .map((item) => _parsePost(item as Map<String, dynamic>))
          .where((p) => p.title.isNotEmpty)
          .toList();

      // Save to cache
      await prefs.setString(_kCache,
          jsonEncode(posts.map((p) => p.toJson()).toList()));
      await prefs.setInt(
          _kCacheTime, DateTime.now().millisecondsSinceEpoch);

      return posts;
    } catch (_) {
      // Network error — return stale cache if available
      return _loadCache(prefs) ?? [];
    }
  }

  // ── Cache ───────────────────────────────────────────────────────────────

  static List<BlogPost>? _loadCache(SharedPreferences prefs) {
    final savedMs = prefs.getInt(_kCacheTime) ?? 0;
    final age     = DateTime.now().millisecondsSinceEpoch - savedMs;
    if (age > _cacheTtlMs) return null;
    final raw = prefs.getString(_kCache);
    if (raw == null || raw.isEmpty) return null;
    try {
      final list = jsonDecode(raw) as List;
      return list
          .map((e) => BlogPost.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (_) {
      return null;
    }
  }

  // ── Parse a WordPress REST API post object ─────────────────────────────

  static BlogPost _parsePost(Map<String, dynamic> json) {
    final id      = json['id'] as int? ?? 0;
    final title   = _stripHtml(json['title']?['rendered']?.toString() ?? '');
    final excerpt = _stripHtml(json['excerpt']?['rendered']?.toString() ?? '');
    final content = _stripHtml(json['content']?['rendered']?.toString() ?? '');
    final link    = json['link']?.toString() ?? '';
    final rawDate = json['date']?.toString() ?? '';
    final date    = _formatDate(rawDate);

    // Featured image via _embedded
    String? imageUrl;
    try {
      final embedded = json['_embedded'] as Map?;
      final media    = embedded?['wp:featuredmedia'] as List?;
      if (media != null && media.isNotEmpty) {
        imageUrl = (media.first as Map?)?['source_url']?.toString();
      }
    } catch (_) {}

    return BlogPost(
      id: id, title: title, excerpt: excerpt,
      content: content, date: date, link: link, imageUrl: imageUrl,
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────────

  static String _stripHtml(String html) {
    // Replace block-level tags with newlines to preserve paragraph breaks
    var s = html
        .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '\n')
        .replaceAll(RegExp(r'</(p|div|h[1-6]|li|blockquote)>',
            caseSensitive: false), '\n')
        .replaceAll(RegExp(r'<[^>]+>'), '')       // strip remaining tags
        .replaceAll(RegExp(r'&amp;'),  '&')
        .replaceAll(RegExp(r'&lt;'),   '<')
        .replaceAll(RegExp(r'&gt;'),   '>')
        .replaceAll(RegExp(r'&nbsp;'), ' ')
        .replaceAll(RegExp(r'&#\d+;'), '')
        .replaceAll(RegExp(r'&[a-z]+;'), '');
    // Collapse excess blank lines
    s = s.replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
    return s;
  }

  static String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      const months = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
      ];
      return '${dt.day} ${months[dt.month]} ${dt.year}';
    } catch (_) {
      return '';
    }
  }
}
