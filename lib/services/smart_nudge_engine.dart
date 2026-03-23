import 'package:mindcore_ai/services/knowledge_snapshot_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';

class SmartNudgeEngine {
  SmartNudgeEngine._();

  static Future<void> scheduleGentleDailyNudge({
    int hour = 8,
    int minute = 0,
  }) async {
    final snapshot = await KnowledgeSnapshotService.buildSnapshot();

    final title = _titleFor(snapshot.dominantState);
    final body = _bodyFor(snapshot.dominantState, snapshot.recommendedFocus);

    await NotificationService.instance.scheduleDailyRecommendationNotification(
      uniqueKey: 'smart_nudge_${snapshot.dominantState}_${snapshot.recommendedFocus}',
      title: title,
      body: body,
      routeName: '/daily-hub',
      routeArguments: {
        'source': 'smart_nudge',
        'focus': snapshot.recommendedFocus,
      },
      hour: hour,
      minute: minute,
    );
  }

  static String _titleFor(String state) {
    switch (state) {
      case 'low':
        return 'A gentle reset is ready';
      case 'fragile':
        return 'Take one calmer step';
      case 'steady':
        return 'Keep your rhythm steady';
      case 'uplifted':
        return 'Build on today’s momentum';
      default:
        return 'Your daily MindCore reset is ready';
    }
  }

  static String _bodyFor(String state, String focus) {
    switch (state) {
      case 'low':
        return 'Open MindCore AI for a softer check-in and one grounding step.';
      case 'fragile':
        return 'A short $focus reset could help you settle before the day speeds up.';
      case 'steady':
        return 'You are doing better than you think. Open the app for a focused daily reset.';
      case 'uplifted':
        return 'You have some momentum today. Open the app and channel it with intention.';
      default:
        return 'Open MindCore AI for your daily reset.';
    }
  }
}
