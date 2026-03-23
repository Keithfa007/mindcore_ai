
// lib/services/stripe_service.dart
import 'package:url_launcher/url_launcher.dart';
import 'package:mindcore_ai/env/env.dart';

final publishable = Env.stripePublishable;
final secret = Env.stripeSecret;


class StripeService {
  static Future<void> openPortal(String url) async {
    final uri = Uri.parse(url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}
