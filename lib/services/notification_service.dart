// lib/services/notification_service.dart
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

// ── Simple data class for check-in messages ───────────────────────────────────
class _CheckInMsg {
  final String title;
  final String body;
  const _CheckInMsg(this.title, this.body);
}

class NotificationService {
  NotificationService._();
  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;
  GlobalKey<NavigatorState>? _navigatorKey;

  // ── Channel IDs ────────────────────────────────────────────────────────────────

  static const String _instantChannelId   = 'instant_channel';
  static const String _instantChannelName = 'Instant Notifications';
  static const String _instantChannelDesc = 'Channel for instant notifications';

  static const String _dailyChannelId   = 'daily_recommendation_channel';
  static const String _dailyChannelName = 'Daily Recommendation';
  static const String _dailyChannelDesc = 'Daily personalised recommendations';

  static const String _checkInChannelId   = 'checkin_channel';
  static const String _checkInChannelName = 'Check-in Notifications';
  static const String _checkInChannelDesc =
      'Friendly check-ins to see how you are doing';

  // ── Notification IDs ──────────────────────────────────────────────────────────

  static const int _dailyNotificationId  = 2000;
  static const int _checkInMorningId     = 4001;
  static const int _checkInAfternoonId   = 4002;
  static const int _checkInEveningId     = 4003;

  static const String _kLastScheduledSignature =
      'recommendation_last_schedule_signature';
  static const String _kCheckInEnabled   = 'checkin_enabled';
  static const String _kCheckInFrequency = 'checkin_frequency';

  // ── Check-in message pool ─────────────────────────────────────────────────────
  // Warm, human messages — not robotic or marketing-like
  static const _checkInMessages = [
    _CheckInMsg('How are you doing? 💙',
        'Take a moment to check in with yourself.'),
    _CheckInMsg('Just thinking of you 🌿',
        'How has your day been so far?'),
    _CheckInMsg('Hey there ✨',
        'How are you feeling right now?'),
    _CheckInMsg('A gentle nudge 🕊️',
        "We're here if you need us."),
    _CheckInMsg('How\'s your day going? ☀️',
        'Take a breath — you\'re doing great.'),
    _CheckInMsg('Checking in with you 💭',
        'How are you really doing today?'),
    _CheckInMsg('A quiet moment 🌸',
        'Be kind to yourself today.'),
    _CheckInMsg('Thinking of you 💚',
        'How is your heart today?'),
    _CheckInMsg('How\'s your evening? 🌙',
        'You deserve a moment of peace.'),
    _CheckInMsg('Just here if you need us 🍃',
        'No pressure — just checking in.'),
  ];

  // ── Init ─────────────────────────────────────────────────────────────────────

  Future<void> init({
    String? timeZoneId,
    GlobalKey<NavigatorState>? navigatorKey,
  }) async {
    if (_initialized) return;
    _navigatorKey = navigatorKey;

    tz.initializeTimeZones();
    final tzId = timeZoneId ?? 'Europe/Malta';
    try {
      tz.setLocalLocation(tz.getLocation(tzId));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('UTC'));
    }

    const androidInit =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);
    await _plugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _handleNotificationResponse,
    );

    if (Platform.isAndroid) {
      final android = _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>();
      await android?.requestNotificationsPermission();

      // Instant channel
      await android?.createNotificationChannel(
        const AndroidNotificationChannel(
          _instantChannelId, _instantChannelName,
          description: _instantChannelDesc,
          importance: Importance.max,
        ),
      );
      // Daily recommendation channel
      await android?.createNotificationChannel(
        const AndroidNotificationChannel(
          _dailyChannelId, _dailyChannelName,
          description: _dailyChannelDesc,
          importance: Importance.max,
        ),
      );
      // Check-in channel
      await android?.createNotificationChannel(
        const AndroidNotificationChannel(
          _checkInChannelId, _checkInChannelName,
          description: _checkInChannelDesc,
          importance: Importance.high,
        ),
      );
    }

    _initialized = true;

    // Auto-schedule check-ins if enabled
    final prefs = await SharedPreferences.getInstance();
    final checkInEnabled  = prefs.getBool(_kCheckInEnabled) ?? true;
    final checkInFreq     = prefs.getInt(_kCheckInFrequency) ?? 2;
    if (checkInEnabled) {
      await scheduleCheckInNotifications(timesPerDay: checkInFreq);
    }
  }

  void _handleNotificationResponse(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;
    try {
      final data      = jsonDecode(payload) as Map<String, dynamic>;
      final routeName = data['routeName']?.toString();
      final arguments = data['arguments'];
      if (routeName == null || routeName.isEmpty) return;
      _navigatorKey?.currentState
          ?.pushNamed(routeName, arguments: arguments);
    } catch (_) {}
  }

  // ── Instant notification ─────────────────────────────────────────────────────

  Future<void> showImmediateNotification({
    required String title,
    required String body,
  }) async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _instantChannelId, _instantChannelName,
        channelDescription: _instantChannelDesc,
        importance: Importance.max,
        priority: Priority.high,
      ),
    );
    await _plugin.show(1000, title, body, details);
  }

  // ── Daily recommendation notification ───────────────────────────────────────────

  Future<void> scheduleDailyRecommendationNotification({
    required String uniqueKey,
    required String title,
    required String body,
    required String routeName,
    Map<String, dynamic>? routeArguments,
    int hour = 8,
    int minute = 0,
    bool openSettingsIfNeeded = false,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final now   = DateTime.now();
    final today = '${now.year}-${now.month}-${now.day}';
    final signature =
        '$today|$hour:$minute|$uniqueKey|$title|$body|${jsonEncode(routeArguments ?? const {})}';
    if (prefs.getString(_kLastScheduledSignature) == signature) return;

    final payload = jsonEncode({
      'routeName': routeName,
      'arguments': routeArguments ?? <String, dynamic>{},
    });

    final nowTz = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(
        tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }

    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _dailyChannelId, _dailyChannelName,
        channelDescription: _dailyChannelDesc,
        importance: Importance.max,
        priority: Priority.high,
      ),
    );

    if (Platform.isAndroid && openSettingsIfNeeded) {
      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestExactAlarmsPermission();
    }

    await _plugin.cancel(_dailyNotificationId);

    Future<void> doSchedule(AndroidScheduleMode mode) => _plugin.zonedSchedule(
          _dailyNotificationId, title, body, scheduled, details,
          payload: payload,
          matchDateTimeComponents: DateTimeComponents.time,
          androidScheduleMode: mode,
        );

    try {
      await doSchedule(AndroidScheduleMode.exactAllowWhileIdle);
    } on PlatformException catch (e) {
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

  Future<void> scheduleDailyResetNotification({
    int hour = 8, int minute = 0, bool openSettingsIfNeeded = false,
  }) => scheduleDailyRecommendationNotification(
        uniqueKey: 'fallback_daily_reset',
        title: 'Your daily recommendation is ready',
        body: 'Open MindCore AI for a calm reset and one gentle next step.',
        routeName: '/home',
        hour: hour, minute: minute,
        openSettingsIfNeeded: openSettingsIfNeeded,
      );

  Future<void> cancelDailyResetNotification() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kLastScheduledSignature);
    await _plugin.cancel(_dailyNotificationId);
  }

  // ── Check-in notifications ─────────────────────────────────────────────────────
  // Scheduled at slightly odd times so they feel human, not robotic.
  // Messages rotate daily from the pool.

  Future<void> scheduleCheckInNotifications({required int timesPerDay}) async {
    await cancelCheckInNotifications();

    final dayOfYear = DateTime.now()
        .difference(DateTime(DateTime.now().year))
        .inDays;

    // Morning: 9:47 AM
    await _scheduleOneCheckIn(
      id: _checkInMorningId,
      hour: 9, minute: 47,
      msgIndex: (dayOfYear * 3) % _checkInMessages.length,
    );

    // Evening: 7:15 PM (always)
    await _scheduleOneCheckIn(
      id: _checkInEveningId,
      hour: 19, minute: 15,
      msgIndex: (dayOfYear * 3 + 2) % _checkInMessages.length,
    );

    // Afternoon: 2:23 PM (only for 3x/day)
    if (timesPerDay >= 3) {
      await _scheduleOneCheckIn(
        id: _checkInAfternoonId,
        hour: 14, minute: 23,
        msgIndex: (dayOfYear * 3 + 1) % _checkInMessages.length,
      );
    }

    // Persist settings
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kCheckInEnabled, true);
    await prefs.setInt(_kCheckInFrequency, timesPerDay);
  }

  Future<void> _scheduleOneCheckIn({
    required int id,
    required int hour,
    required int minute,
    required int msgIndex,
  }) async {
    final msg     = _checkInMessages[msgIndex];
    final payload = jsonEncode({'routeName': '/home'});

    final nowTz = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(
        tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }

    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _checkInChannelId, _checkInChannelName,
        channelDescription: _checkInChannelDesc,
        importance: Importance.high,
        priority: Priority.high,
      ),
    );

    try {
      await _plugin.zonedSchedule(
        id, msg.title, msg.body, scheduled, details,
        payload: payload,
        matchDateTimeComponents: DateTimeComponents.time,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      );
    } catch (_) {}
  }

  Future<void> cancelCheckInNotifications() async {
    await _plugin.cancel(_checkInMorningId);
    await _plugin.cancel(_checkInAfternoonId);
    await _plugin.cancel(_checkInEveningId);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kCheckInEnabled, false);
  }

  Future<void> cancelAll() => _plugin.cancelAll();
}
