// lib/services/notification_service.dart
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show MethodChannel, PlatformException;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class _CheckInMsg {
  final String title;
  final String body;
  const _CheckInMsg(this.title, this.body);
}

class NotificationService {
  NotificationService._();
  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  static const _settingsChannel = MethodChannel('com.mindcoreai.app/settings');
  bool _initialized = false;
  GlobalKey<NavigatorState>? _navigatorKey;

  // Channel IDs
  static const _instantChannelId        = 'instant_channel';
  static const _instantChannelName      = 'Instant Notifications';
  static const _instantChannelDesc      = 'Channel for instant notifications';
  static const _dailyChannelId          = 'daily_recommendation_channel';
  static const _dailyChannelName        = 'Daily Recommendation';
  static const _dailyChannelDesc        = 'Daily personalised recommendations';
  static const _checkInChannelId        = 'checkin_channel';
  static const _checkInChannelName      = 'Check-in Notifications';
  static const _checkInChannelDesc      = 'Friendly check-ins to see how you are doing';
  static const _blogChannelId           = 'blog_channel';
  static const _blogChannelName         = 'New Articles';
  static const _blogChannelDesc         = 'Notifies you when a new article is published';
  static const _weeklySummaryChannelId   = 'weekly_summary_channel';
  static const _weeklySummaryChannelName = 'Weekly Progress';
  static const _weeklySummaryChannelDesc = 'A warm Sunday summary of your wellness journey';
  static const _sleepChannelId           = 'sleep_ritual_channel';
  static const _sleepChannelName         = 'Sleep Ritual';
  static const _sleepChannelDesc         = 'Morning and evening check-in reminders';
  static const _trialChannelId           = 'trial_nudge_channel';
  static const _trialChannelName         = 'Trial Reminders';
  static const _trialChannelDesc         = 'Reminders during your free trial';

  // Notification IDs
  static const int _dailyNotificationId   = 2000;
  static const int _checkInMorningId      = 4001;
  static const int _checkInAfternoonId    = 4002;
  static const int _checkInEveningId      = 4003;
  static const int _blogNotificationId    = 5001;
  static const int _weeklySummaryId       = 6001;
  static const int _sleepEveningId        = 7001;
  static const int _sleepMorningId        = 7002;
  static const int _trialNudgeDay2Id      = 8001;
  static const int _trialNudgeDay3Id      = 8002;

  // Prefs keys
  static const String _kLastScheduledSignature = 'recommendation_last_schedule_signature';
  static const String _kCheckInEnabled         = 'checkin_enabled';
  static const String _kCheckInFrequency       = 'checkin_frequency';
  static const String _kNeedsReschedule        = 'needs_notification_reschedule';
  static const String _kBatteryPromptShown     = 'battery_opt_prompt_shown';

  static const _checkInMessages = [
    _CheckInMsg('How are you doing? \ud83d\udc99', 'Take a moment to check in with yourself.'),
    _CheckInMsg('Just thinking of you \ud83c\udf3f', 'How has your day been so far?'),
    _CheckInMsg('Hey there \u2728', 'How are you feeling right now?'),
    _CheckInMsg('A gentle nudge \ud83d\udd4a\ufe0f', "We're here if you need us."),
    _CheckInMsg('How\'s your day going? \u2600\ufe0f', 'Take a breath \u2014 you\'re doing great.'),
    _CheckInMsg('Checking in with you \ud83d\udcad', 'How are you really doing today?'),
    _CheckInMsg('A quiet moment \ud83c\udf38', 'Be kind to yourself today.'),
    _CheckInMsg('Thinking of you \ud83d\udc9a', 'How is your heart today?'),
    _CheckInMsg('How\'s your evening? \ud83c\udf19', 'You deserve a moment of peace.'),
    _CheckInMsg('Just here if you need us \ud83c\udf43', 'No pressure \u2014 just checking in.'),
  ];

  static const _weeklySummaryMessages = [
    _CheckInMsg('Your week, reflected back \ud83c\udf1f', 'You showed up this week. Open MindCore AI to see how far you have come.'),
    _CheckInMsg('Sunday check-in \ud83c\udf19', 'Every small step this week counted. Take a moment to acknowledge that.'),
    _CheckInMsg('You made it through another week \ud83d\udc9a', 'Open MindCore AI to reflect on your week and start the next one gently.'),
    _CheckInMsg('A quiet Sunday moment \u2728', 'How was your week really? Take 2 minutes to check in with yourself.'),
    _CheckInMsg('Weekly reflection time \ud83c\udf3f', 'Progress is not always visible. But you kept going. That matters.'),
  ];

  Future<void> init({
    String? timeZoneId,
    GlobalKey<NavigatorState>? navigatorKey,
  }) async {
    if (_initialized) return;
    _navigatorKey = navigatorKey;

    tz.initializeTimeZones();
    final tzId = timeZoneId ?? 'Europe/Malta';
    try { tz.setLocalLocation(tz.getLocation(tzId)); }
    catch (_) { tz.setLocalLocation(tz.getLocation('UTC')); }

    const androidInit  = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);
    await _plugin.initialize(initSettings,
        onDidReceiveNotificationResponse: _handleNotificationResponse);

    if (Platform.isAndroid) {
      final android = _plugin.resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin>();
      await android?.requestNotificationsPermission();
      for (final ch in [
        const AndroidNotificationChannel(_instantChannelId,   _instantChannelName,   description: _instantChannelDesc,        importance: Importance.max),
        const AndroidNotificationChannel(_dailyChannelId,     _dailyChannelName,     description: _dailyChannelDesc,          importance: Importance.max),
        const AndroidNotificationChannel(_checkInChannelId,   _checkInChannelName,   description: _checkInChannelDesc,        importance: Importance.high),
        const AndroidNotificationChannel(_blogChannelId,      _blogChannelName,      description: _blogChannelDesc,           importance: Importance.high),
        const AndroidNotificationChannel(_weeklySummaryChannelId, _weeklySummaryChannelName, description: _weeklySummaryChannelDesc, importance: Importance.high),
        const AndroidNotificationChannel(_sleepChannelId,     _sleepChannelName,     description: _sleepChannelDesc,          importance: Importance.high),
        const AndroidNotificationChannel(_trialChannelId,     _trialChannelName,     description: _trialChannelDesc,          importance: Importance.high),
      ]) { await android?.createNotificationChannel(ch); }
    }

    _initialized = true;

    final prefs = await SharedPreferences.getInstance();
    final needsReschedule = prefs.getBool(_kNeedsReschedule) ?? false;
    if (needsReschedule) {
      await prefs.remove(_kNeedsReschedule);
      await prefs.remove(_kLastScheduledSignature);
    }

    final checkInEnabled = prefs.getBool(_kCheckInEnabled) ?? true;
    final checkInFreq    = prefs.getInt(_kCheckInFrequency) ?? 2;
    if (checkInEnabled) await scheduleCheckInNotifications(timesPerDay: checkInFreq);
    await scheduleWeeklySummary();
  }

  void _handleNotificationResponse(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;
    try {
      final data      = jsonDecode(payload) as Map<String, dynamic>;
      final routeName = data['routeName']?.toString();
      final arguments = data['arguments'];
      if (routeName == null || routeName.isEmpty) return;
      _navigatorKey?.currentState?.pushNamed(routeName, arguments: arguments);
    } catch (_) {}
  }

  // ── Battery ────────────────────────────────────────────────────────────

  Future<bool> isIgnoringBatteryOptimizations() async {
    if (!Platform.isAndroid) return true;
    try {
      final result = await _settingsChannel.invokeMethod<bool>('isIgnoringBatteryOptimizations');
      return result ?? false;
    } catch (_) { return false; }
  }

  Future<void> promptBatteryOptimizationExemption(BuildContext context) async {
    if (!Platform.isAndroid) return;
    final already = await isIgnoringBatteryOptimizations();
    if (already) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('\u2705 Background notifications are already enabled')));
      return;
    }
    if (!context.mounted) return;
    final go = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Allow background notifications'),
        content: const Text(
          'To receive check-in reminders when the app is closed, tap Allow on the next screen.\n\n'
          'Select \u201cUnrestricted\u201d or \u201cDon\u2019t optimise\u201d for battery usage.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Not now')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true),  child: const Text('Allow')),
        ],
      ),
    );
    if (go != true) return;
    try { await _settingsChannel.invokeMethod('openBatterySettings'); } catch (_) {}
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kBatteryPromptShown, true);
  }

  Future<void> promptBatteryOptimizationIfNeeded(BuildContext context) async {
    if (!Platform.isAndroid) return;
    final prefs  = await SharedPreferences.getInstance();
    final shown  = prefs.getBool(_kBatteryPromptShown) ?? false;
    if (shown) return;
    final already = await isIgnoringBatteryOptimizations();
    if (already) { await prefs.setBool(_kBatteryPromptShown, true); return; }
    if (!context.mounted) return;
    await Future.delayed(const Duration(seconds: 3));
    if (!context.mounted) return;
    await promptBatteryOptimizationExemption(context);
  }

  // ── Immediate / blog ───────────────────────────────────────────────────

  Future<void> showImmediateNotification({required String title, required String body}) async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_instantChannelId, _instantChannelName,
          channelDescription: _instantChannelDesc, importance: Importance.max, priority: Priority.high),
    );
    await _plugin.show(1000, title, body, details);
  }

  Future<void> showNewBlogPostNotification({required String postTitle}) async {
    final payload = jsonEncode({'routeName': '/blog'});
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_blogChannelId, _blogChannelName,
          channelDescription: _blogChannelDesc, importance: Importance.high, priority: Priority.high,
          styleInformation: BigTextStyleInformation('')),
    );
    await _plugin.show(_blogNotificationId, 'New article \ud83d\udcd6', postTitle, details, payload: payload);
  }

  // ── Trial nudges ─────────────────────────────────────────────────────────

  Future<void> scheduleTrialNudges(DateTime trialStart) async {
    final payload = jsonEncode({'routeName': '/home'});

    // Day 2 nudge: 24 hours after trial start, at 10am
    final day2 = trialStart.add(const Duration(days: 1));
    final day2Time = tz.TZDateTime(
      tz.local, day2.year, day2.month, day2.day, 10, 0,
    );

    // Day 3 nudge: 48 hours after trial start, at 9am
    final day3 = trialStart.add(const Duration(days: 2));
    final day3Time = tz.TZDateTime(
      tz.local, day3.year, day3.month, day3.day, 9, 0,
    );

    const day2Details = NotificationDetails(
      android: AndroidNotificationDetails(_trialChannelId, _trialChannelName,
          channelDescription: _trialChannelDesc, importance: Importance.high, priority: Priority.high),
    );

    try {
      await _plugin.zonedSchedule(
        _trialNudgeDay2Id,
        'How\'s it going? \ud83d\udc99',
        'You\'ve been using MindCore AI for 2 days. Your trial ends tomorrow \u2014 how\'s it feeling?',
        day2Time, day2Details,
        payload: payload,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    } catch (_) {}

    try {
      await _plugin.zonedSchedule(
        _trialNudgeDay3Id,
        'Your trial ends today \u23f3',
        'Everything you\'ve shared is saved and waiting for you. Subscribe to keep going.',
        day3Time, day2Details,
        payload: payload,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    } catch (_) {}
  }

  Future<void> cancelTrialNudges() async {
    await _plugin.cancel(_trialNudgeDay2Id);
    await _plugin.cancel(_trialNudgeDay3Id);
  }

  // ── Daily recommendation ─────────────────────────────────────────────────

  Future<void> scheduleDailyRecommendationNotification({
    required String uniqueKey, required String title, required String body,
    required String routeName, Map<String, dynamic>? routeArguments,
    int hour = 8, int minute = 0, bool openSettingsIfNeeded = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final now   = DateTime.now();
    final today = '${now.year}-${now.month}-${now.day}';
    final signature = '$today|$hour:$minute|$uniqueKey|$title|$body|${jsonEncode(routeArguments ?? const {})}';
    if (prefs.getString(_kLastScheduledSignature) == signature) return;
    final payload  = jsonEncode({'routeName': routeName, 'arguments': routeArguments ?? <String, dynamic>{}});
    final nowTz    = tz.TZDateTime.now(tz.local);
    var scheduled  = tz.TZDateTime(tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) scheduled = scheduled.add(const Duration(days: 1));
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_dailyChannelId, _dailyChannelName,
          channelDescription: _dailyChannelDesc, importance: Importance.max, priority: Priority.high),
    );
    await _plugin.cancel(_dailyNotificationId);
    Future<void> doSchedule(AndroidScheduleMode mode) => _plugin.zonedSchedule(
      _dailyNotificationId, title, body, scheduled, details,
      payload: payload, matchDateTimeComponents: DateTimeComponents.time, androidScheduleMode: mode,
    );
    try { await doSchedule(AndroidScheduleMode.exactAllowWhileIdle); }
    on PlatformException catch (e) {
      if (e.code == 'exact_alarms_not_permitted') {
        await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle);
      } else {
        try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
      }
    } catch (_) {
      try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
    }
    await prefs.setString(_kLastScheduledSignature, signature);
  }

  Future<void> scheduleDailyResetNotification({int hour = 8, int minute = 0, bool openSettingsIfNeeded = false}) =>
      scheduleDailyRecommendationNotification(
        uniqueKey: 'fallback_daily_reset',
        title: 'Your daily recommendation is ready',
        body: 'Open MindCore AI for a calm reset and one gentle next step.',
        routeName: '/home', hour: hour, minute: minute,
        openSettingsIfNeeded: openSettingsIfNeeded,
      );

  Future<void> cancelDailyResetNotification() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kLastScheduledSignature);
    await _plugin.cancel(_dailyNotificationId);
  }

  // ── Check-in ────────────────────────────────────────────────────────────

  Future<void> scheduleCheckInNotifications({required int timesPerDay}) async {
    await cancelCheckInNotifications();
    final dayOfYear = DateTime.now().difference(DateTime(DateTime.now().year)).inDays;
    await _scheduleOneCheckIn(id: _checkInMorningId, hour: 9, minute: 47, msgIndex: (dayOfYear * 3) % _checkInMessages.length);
    await _scheduleOneCheckIn(id: _checkInEveningId, hour: 19, minute: 15, msgIndex: (dayOfYear * 3 + 2) % _checkInMessages.length);
    if (timesPerDay >= 3) {
      await _scheduleOneCheckIn(id: _checkInAfternoonId, hour: 14, minute: 23, msgIndex: (dayOfYear * 3 + 1) % _checkInMessages.length);
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kCheckInEnabled, true);
    await prefs.setInt(_kCheckInFrequency, timesPerDay);
  }

  Future<void> _scheduleOneCheckIn({required int id, required int hour, required int minute, required int msgIndex}) async {
    final msg     = _checkInMessages[msgIndex];
    final payload = jsonEncode({'routeName': '/home'});
    final nowTz   = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) scheduled = scheduled.add(const Duration(days: 1));
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_checkInChannelId, _checkInChannelName,
          channelDescription: _checkInChannelDesc, importance: Importance.high, priority: Priority.high),
    );
    Future<void> doSchedule(AndroidScheduleMode mode) => _plugin.zonedSchedule(
      id, msg.title, msg.body, scheduled, details,
      payload: payload, matchDateTimeComponents: DateTimeComponents.time, androidScheduleMode: mode,
    );
    try { await doSchedule(AndroidScheduleMode.exactAllowWhileIdle); }
    on PlatformException catch (e) {
      if (e.code == 'exact_alarms_not_permitted') {
        try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
      } else {
        try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
      }
    } catch (_) {
      try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
    }
  }

  Future<void> cancelCheckInNotifications() async {
    await _plugin.cancel(_checkInMorningId);
    await _plugin.cancel(_checkInAfternoonId);
    await _plugin.cancel(_checkInEveningId);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kCheckInEnabled, false);
  }

  // ── Sleep Ritual ─────────────────────────────────────────────────────────

  Future<void> scheduleSleepRitualNotifications({
    required TimeOfDay eveningTime, required TimeOfDay morningTime,
  }) async {
    await cancelSleepRitualNotifications();
    await _scheduleOneSleepNotif(
      id: _sleepEveningId, title: 'Evening check-in \ud83c\udf19',
      body: 'How did today go? Take 30 seconds.',
      hour: eveningTime.hour, minute: eveningTime.minute, mode: 'evening',
    );
    await _scheduleOneSleepNotif(
      id: _sleepMorningId, title: 'Good morning \u2600\ufe0f',
      body: 'How are you feeling today?',
      hour: morningTime.hour, minute: morningTime.minute, mode: 'morning',
    );
  }

  Future<void> _scheduleOneSleepNotif({
    required int id, required String title, required String body,
    required int hour, required int minute, required String mode,
  }) async {
    final payload = jsonEncode({'routeName': '/sleep-ritual', 'arguments': {'mode': mode}});
    final nowTz   = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) scheduled = scheduled.add(const Duration(days: 1));
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_sleepChannelId, _sleepChannelName,
          channelDescription: _sleepChannelDesc, importance: Importance.high, priority: Priority.high),
    );
    Future<void> doSchedule(AndroidScheduleMode m) => _plugin.zonedSchedule(
      id, title, body, scheduled, details,
      payload: payload, matchDateTimeComponents: DateTimeComponents.time, androidScheduleMode: m,
    );
    try { await doSchedule(AndroidScheduleMode.exactAllowWhileIdle); }
    on PlatformException catch (e) {
      if (e.code == 'exact_alarms_not_permitted') {
        try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
      } else {
        try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
      }
    } catch (_) {
      try { await doSchedule(AndroidScheduleMode.inexactAllowWhileIdle); } catch (_) {}
    }
  }

  Future<void> cancelSleepRitualNotifications() async {
    await _plugin.cancel(_sleepEveningId);
    await _plugin.cancel(_sleepMorningId);
  }

  // ── Weekly summary ────────────────────────────────────────────────────────

  Future<void> scheduleWeeklySummary() async {
    try {
      final weekNumber = DateTime.now().difference(DateTime(DateTime.now().year, 1, 1)).inDays ~/ 7;
      final msg = _weeklySummaryMessages[weekNumber % _weeklySummaryMessages.length];
      await _scheduleWeeklySummaryNotification(title: msg.title, body: msg.body);
    } catch (_) {}
  }

  Future<void> scheduleWeeklySummaryWithStat(String statLine) async {
    try {
      final title = 'Your week, reflected back \ud83c\udf1f';
      final body  = statLine.isNotEmpty
          ? '$statLine. Tap to see your full journey.'
          : 'You showed up this week. Open MindCore AI to see how far you have come.';
      await _scheduleWeeklySummaryNotification(title: title, body: body);
    } catch (_) {}
  }

  Future<void> _scheduleWeeklySummaryNotification({required String title, required String body}) async {
    final payload = jsonEncode({'routeName': '/journey'});
    final nowTz   = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(tz.local, nowTz.year, nowTz.month, nowTz.day, 19, 0);
    while (scheduled.weekday != DateTime.sunday || scheduled.isBefore(nowTz)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }
    const details = NotificationDetails(
      android: AndroidNotificationDetails(_weeklySummaryChannelId, _weeklySummaryChannelName,
          channelDescription: _weeklySummaryChannelDesc, importance: Importance.high, priority: Priority.high),
    );
    await _plugin.cancel(_weeklySummaryId);
    await _plugin.zonedSchedule(_weeklySummaryId, title, body, scheduled, details,
        payload: payload,
        matchDateTimeComponents: DateTimeComponents.dayOfWeekAndTime,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle);
  }

  Future<void> cancelWeeklySummary() => _plugin.cancel(_weeklySummaryId).then((_) {});
  Future<void> cancelAll() => _plugin.cancelAll();
}
