// lib/services/notification_service.dart
import 'dart:convert';
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show PlatformException;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:timezone/data/latest_all.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class NotificationService {
  NotificationService._();
  static final NotificationService instance = NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  bool _initialized = false;
  GlobalKey<NavigatorState>? _navigatorKey;

  static const String _instantChannelId = 'instant_channel';
  static const String _instantChannelName = 'Instant Notifications';
  static const String _instantChannelDesc = 'Channel for instant notifications';

  static const String _dailyChannelId = 'daily_recommendation_channel';
  static const String _dailyChannelName = 'Daily Recommendation';
  static const String _dailyChannelDesc = 'Daily personalized recommendations';

  static const int _dailyNotificationId = 2000;
  static const String _kLastScheduledSignature = 'recommendation_last_schedule_signature';

  Future<void> init({String? timeZoneId, GlobalKey<NavigatorState>? navigatorKey}) async {
    if (_initialized) return;
    _navigatorKey = navigatorKey;

    tz.initializeTimeZones();
    final tzId = timeZoneId ?? 'Europe/Malta';
    try {
      tz.setLocalLocation(tz.getLocation(tzId));
    } catch (_) {
      tz.setLocalLocation(tz.getLocation('UTC'));
    }

    const androidInit = AndroidInitializationSettings('@mipmap/ic_launcher');
    const initSettings = InitializationSettings(android: androidInit);
    await _plugin.initialize(
      initSettings,
      onDidReceiveNotificationResponse: _handleNotificationResponse,
    );

    if (Platform.isAndroid) {
      final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
      await android?.requestNotificationsPermission();
      await android?.createNotificationChannel(const AndroidNotificationChannel(
        _instantChannelId,
        _instantChannelName,
        description: _instantChannelDesc,
        importance: Importance.max,
      ));
      await android?.createNotificationChannel(const AndroidNotificationChannel(
        _dailyChannelId,
        _dailyChannelName,
        description: _dailyChannelDesc,
        importance: Importance.max,
      ));
    }

    _initialized = true;
  }

  void _handleNotificationResponse(NotificationResponse response) {
    final payload = response.payload;
    if (payload == null || payload.isEmpty) return;

    try {
      final data = jsonDecode(payload) as Map<String, dynamic>;
      final routeName = data['routeName']?.toString();
      final arguments = data['arguments'];
      if (routeName == null || routeName.isEmpty) return;
      _navigatorKey?.currentState?.pushNamed(routeName, arguments: arguments);
    } catch (_) {}
  }

  Future<void> showImmediateNotification({
    required String title,
    required String body,
  }) async {
    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _instantChannelId,
        _instantChannelName,
        channelDescription: _instantChannelDesc,
        importance: Importance.max,
        priority: Priority.high,
      ),
    );
    await _plugin.show(1000, title, body, details);
  }

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
    final now = DateTime.now();
    final today = '${now.year}-${now.month}-${now.day}';
    final signature = '$today|$hour:$minute|$uniqueKey|$title|$body|${jsonEncode(routeArguments ?? const {})}';
    if (prefs.getString(_kLastScheduledSignature) == signature) {
      return;
    }

    final payload = jsonEncode({
      'routeName': routeName,
      'arguments': routeArguments ?? <String, dynamic>{},
    });

    final nowTz = tz.TZDateTime.now(tz.local);
    var scheduled = tz.TZDateTime(tz.local, nowTz.year, nowTz.month, nowTz.day, hour, minute);
    if (scheduled.isBefore(nowTz)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }

    const details = NotificationDetails(
      android: AndroidNotificationDetails(
        _dailyChannelId,
        _dailyChannelName,
        channelDescription: _dailyChannelDesc,
        importance: Importance.max,
        priority: Priority.high,
      ),
    );

    final android = _plugin.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    if (Platform.isAndroid && openSettingsIfNeeded) {
      await android?.requestExactAlarmsPermission();
    }

    Future<void> _schedule(AndroidScheduleMode mode) {
      return _plugin.zonedSchedule(
        _dailyNotificationId,
        title,
        body,
        scheduled,
        details,
        payload: payload,
        matchDateTimeComponents: DateTimeComponents.time,
        androidScheduleMode: mode,
      );
    }

    await _plugin.cancel(_dailyNotificationId);

    try {
      await _schedule(AndroidScheduleMode.exactAllowWhileIdle);
    } on PlatformException catch (e) {
      if (e.code == 'exact_alarms_not_permitted') {
        await _schedule(AndroidScheduleMode.inexactAllowWhileIdle);
      } else {
        try {
          await _schedule(AndroidScheduleMode.inexactAllowWhileIdle);
        } catch (_) {}
      }
    } catch (_) {
      try {
        await _schedule(AndroidScheduleMode.inexactAllowWhileIdle);
      } catch (_) {}
    }

    await prefs.setString(_kLastScheduledSignature, signature);
  }

  Future<void> scheduleDailyResetNotification({
    int hour = 8,
    int minute = 0,
    bool openSettingsIfNeeded = false,
  }) {
    return scheduleDailyRecommendationNotification(
      uniqueKey: 'fallback_daily_reset',
      title: 'Daily recommendation ready',
      body: 'Open MindCore AI for a calm reset and one gentle next step.',
      routeName: '/home',
      hour: hour,
      minute: minute,
      openSettingsIfNeeded: openSettingsIfNeeded,
    );
  }

  Future<void> cancelDailyResetNotification() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kLastScheduledSignature);
    await _plugin.cancel(_dailyNotificationId);
  }

  Future<void> cancelAll() => _plugin.cancelAll();
}
