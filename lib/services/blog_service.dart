// lib/services/blog_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:mindcore_ai/services/notification_service.dart';

class BlogPost {
  final int    id;
  final String title;
  final String excerpt;
  final String content;   // Markdown-converted (links preserved as [text](url))
  final String date;
  final String link;
  final String? imageUrl;

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
        'id': id, 'title': title, 'excerpt': excerpt,
        'content': content, 'date': date, 'link': link, 'imageUrl': imageUrl,
      };

  factory BlogPost.fromJson(Map<String, dynamic> j) => BlogPost(
        id:       (j['id']       as int?)    ?? 0,
        title:    (j['title']    as String?) ?? '',
        excerpt:  (j['excerpt']  as String?) ?? '',
        content:  (j['content']  as String?) ?? '',
        date:     (j['date']     as String?) ?? '',
        link:     (j['link']     as String?) ?? '',
        imageUrl:  j['imageUrl'] as String?,
      );
}

class BlogService {
  static const _endpoint =
      'https://mindcoreai.eu/wp-json/wp/v2/posts'
      '?_embed&per_page=20&orderby=date&order=desc&status=publish';

  static const _kCache      = 'blog_posts_v2';
  static const _kCacheTime  = 'blog_posts_time_v2';
  static const _kLastSeenId = 'blog_last_seen_post_id';
  static const _cacheTtlMs  = 60 * 60 * 1000;

  // ── Public API ──────────────────────────────────────────────────────

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
      if (response.statusCode != 200) return _loadCache(prefs) ?? [];
      final raw   = jsonDecode(response.body) as List;
      final posts = raw
          .map((item) => _parsePost(item as Map<String, dynamic>))
          .where((p) => p.title.isNotEmpty)
          .toList();
      await prefs.setString(_kCache, jsonEncode(posts.map((p) => p.toJson()).toList()));
      await prefs.setInt(_kCacheTime, DateTime.now().millisecondsSinceEpoch);
      return posts;
    } catch (_) {
      return _loadCache(prefs) ?? [];
    }
  }

  static Future<void> checkForNewPost() async {
    try {
      final response = await http
          .get(Uri.parse(
              'https://mindcoreai.eu/wp-json/wp/v2/posts'
              '?per_page=1&orderby=date&order=desc&status=publish'))
          .timeout(const Duration(seconds: 10));
      if (response.statusCode != 200) return;
      final raw = jsonDecode(response.body) as List;
      if (raw.isEmpty) return;
      final latest   = raw.first as Map<String, dynamic>;
      final latestId = latest['id'] as int? ?? 0;
      if (latestId == 0) return;
      final prefs      = await SharedPreferences.getInstance();
      final lastSeenId = prefs.getInt(_kLastSeenId) ?? 0;
      if (latestId > lastSeenId) {
        await prefs.setInt(_kLastSeenId, latestId);
        if (lastSeenId > 0) {
          final title = _stripHtml(latest['title']?['rendered']?.toString() ?? 'New article');
          await NotificationService.instance.showNewBlogPostNotification(postTitle: title);
        }
      }
    } catch (_) {}
  }

  // ── Cache ────────────────────────────────────────────────────────────

  static List<BlogPost>? _loadCache(SharedPreferences prefs) {
    final savedMs = prefs.getInt(_kCacheTime) ?? 0;
    if (DateTime.now().millisecondsSinceEpoch - savedMs > _cacheTtlMs) return null;
    final raw = prefs.getString(_kCache);
    if (raw == null || raw.isEmpty) return null;
    try {
      final list = jsonDecode(raw) as List;
      return list.map((e) => BlogPost.fromJson(Map<String, dynamic>.from(e as Map))).toList();
    } catch (_) { return null; }
  }

  // ── Parse ────────────────────────────────────────────────────────────

  static BlogPost _parsePost(Map<String, dynamic> json) {
    final id      = json['id'] as int? ?? 0;
    final title   = _stripHtml(json['title']?['rendered']?.toString() ?? '');
    final excerpt = _stripHtml(json['excerpt']?['rendered']?.toString() ?? '');
    final content = _htmlToMarkdown(json['content']?['rendered']?.toString() ?? '');
    final link    = json['link']?.toString() ?? '';
    final date    = _formatDate(json['date']?.toString() ?? '');

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

  // ── HTML → Markdown ──────────────────────────────────────────────────────────
  //
  // Converts HTML to Markdown so links are preserved as [text](url)
  // and rendered as tappable by flutter_markdown.
  // Note: uses non-raw strings (double-quoted) for regexes that need
  // to match both single and double quotes without Dart parse errors.

  static String _htmlToMarkdown(String html) {
    var s = html;

    // Links — double-quoted href
    s = s.replaceAllMapped(
      RegExp('<a[^>]*?href="([^"]+)"[^>]*>(.*?)</a>',
             caseSensitive: false, dotAll: true),
      (m) {
        final url  = m.group(1)?.trim() ?? '';
        final text = _stripHtml(m.group(2) ?? '').trim();
        if (url.isEmpty) return text;
        return '[$text]($url)';
      },
    );

    // Links — single-quoted href
    s = s.replaceAllMapped(
      RegExp("<a[^>]*?href='([^']+)'[^>]*>(.*?)</a>",
             caseSensitive: false, dotAll: true),
      (m) {
        final url  = m.group(1)?.trim() ?? '';
        final text = _stripHtml(m.group(2) ?? '').trim();
        if (url.isEmpty) return text;
        return '[$text]($url)';
      },
    );

    // Bold
    s = s.replaceAllMapped(
      RegExp(r'<(?:strong|b)>(.*?)</(?:strong|b)>',
             caseSensitive: false, dotAll: true),
      (m) => '**${m.group(1)}**',
    );

    // Italic
    s = s.replaceAllMapped(
      RegExp(r'<(?:em|i)>(.*?)</(?:em|i)>',
             caseSensitive: false, dotAll: true),
      (m) => '*${m.group(1)}*',
    );

    // Headings
    s = s.replaceAllMapped(
      RegExp(r'<h([1-6])[^>]*>(.*?)</h[1-6]>',
             caseSensitive: false, dotAll: true),
      (m) {
        final hashes = '#' * int.parse(m.group(1)!);
        final text   = _stripHtml(m.group(2) ?? '').trim();
        return '\n$hashes $text\n';
      },
    );

    // List items
    s = s.replaceAllMapped(
      RegExp(r'<li[^>]*>(.*?)</li>',
             caseSensitive: false, dotAll: true),
      (m) => '\n- ${_stripHtml(m.group(1) ?? '').trim()}',
    );

    // Block-level line breaks
    s = s
        .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), '  \n')
        .replaceAll(
            RegExp(r'</(p|div|h[1-6]|ul|ol|blockquote)>', caseSensitive: false),
            '\n');

    // Strip remaining tags
    s = s.replaceAll(RegExp(r'<[^>]+>'), '');

    // Decode entities
    s = s
        .replaceAll('&amp;',  '&')
        .replaceAll('&lt;',   '<')
        .replaceAll('&gt;',   '>')
        .replaceAll('&nbsp;', ' ')
        .replaceAll('&#038;', '&')
        .replaceAll('&#8216;', '\u2018')
        .replaceAll('&#8217;', '\u2019')
        .replaceAll('&#8220;', '\u201c')
        .replaceAll('&#8221;', '\u201d')
        .replaceAll('&#8211;', '\u2013')
        .replaceAll('&#8212;', '\u2014')
        .replaceAll(RegExp(r'&#\d+;'), '')
        .replaceAll(RegExp(r'&[a-z]+;'), '');

    s = s.replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
    return s;
  }

  // ── Plain text stripper (title / excerpt) ───────────────────────────────────

  static String _stripHtml(String html) {
    var s = html
        .replaceAll(RegExp(r'<br\s*/?>', caseSensitive: false), ' ')
        .replaceAll(RegExp(r'</(p|div|h[1-6]|li|blockquote)>', caseSensitive: false), ' ')
        .replaceAll(RegExp(r'<[^>]+>'), '')
        .replaceAll('&amp;',  '&')
        .replaceAll('&lt;',   '<')
        .replaceAll('&gt;',   '>')
        .replaceAll('&nbsp;', ' ')
        .replaceAll(RegExp(r'&#\d+;'), '')
        .replaceAll(RegExp(r'&[a-z]+;'), '');
    return s.replaceAll(RegExp(r'\s{2,}'), ' ').trim();
  }

  static String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      const months = [
        '', 'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
      ];
      return '${dt.day} ${months[dt.month]} ${dt.year}';
    } catch (_) { return ''; }
  }
}
