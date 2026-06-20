// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import 'pages/post_login_gate.dart';
import 'theme/app_theme.dart';
import 'pages/home_screen.dart';
import 'pages/chat_screen.dart';
import 'pages/daily_hub_screen.dart';
import 'pages/breathe_screen.dart';
import 'pages/mood_history_screen.dart';
import 'pages/frequently_asked_screen.dart';
import 'pages/profile_screen.dart';
import 'pages/login_screen.dart';
import 'pages/reset_screen.dart';
import 'pages/chat_persona_screen.dart';
import 'pages/relax_audio_screen.dart';
import 'pages/settings_screen.dart';
import 'pages/guided_sessions_screen.dart';
import 'pages/paywall_screen.dart';
import 'pages/voice_chat_screen.dart';
import 'pages/sos_screen.dart';
import 'pages/disclaimer_screen.dart';
import 'pages/blog_screen.dart';
import 'pages/journey_screen.dart';
import 'pages/sleep_ritual_screen.dart';
import 'pages/wins_screen.dart';
import 'pages/truth_deck_screen.dart';

import 'pages/helpers/route_observer.dart';
import 'services/settings_service.dart';
import 'services/notification_service.dart';
import 'services/openai_tts_service.dart';
import 'services/premium_service.dart';
import 'services/usage_service.dart';

final GlobalKey<NavigatorState> appNavigatorKey = GlobalKey<NavigatorState>();

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await SettingsService.init();
  try {
    await dotenv.load(fileName: 'assets/config/env/.env');
  } catch (_) {
    try { await dotenv.load(fileName: '.env'); } catch (_) {}
  }
  await OpenAiTtsService.instance.init();
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp, DeviceOrientation.portraitDown,
  ]);
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  final messaging = FirebaseMessaging.instance;
  await messaging.requestPermission(alert: true, badge: true, sound: true);
  await messaging.subscribeToTopic('relax_audio_updates');
  FirebaseMessaging.onMessage.listen((RemoteMessage message) {
    final screen = message.data['screen'];
    if (screen == 'relax_audio') appNavigatorKey.currentState?.pushNamed('/relax-audio');
  });
  FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
    final screen = message.data['screen'];
    if (screen == 'relax_audio') appNavigatorKey.currentState?.pushNamed('/relax-audio');
  });
  await PremiumService.init();
  await UsageService.instance.init();
  await NotificationService.instance.init(navigatorKey: appNavigatorKey);
  runApp(const MindCoreApp());
}

class MindCoreApp extends StatelessWidget {
  const MindCoreApp({super.key});
  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: SettingsService.themeMode,
      builder: (context, mode, _) {
        return MaterialApp(
          navigatorKey: appNavigatorKey,
          title: 'MindCore AI',
          debugShowCheckedModeBanner: false,
          themeMode: mode,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          navigatorObservers: [appRouteObserver],
          routes: {
            '/home':             (_) => const HomeScreen(),
            '/chat':             (_) => const ChatScreen(),
            '/daily-hub':        (_) => const DailyHubScreen(),
            '/breathe':          (_) => const BreatheScreen(),
            '/reset':            (_) => const ResetScreen(),
            '/mood-history':     (_) => const MoodHistoryScreen(),
            '/frequently-asked': (_) => const FrequentlyAskedPage(),
            '/profile':          (_) => const ProfileScreen(),
            '/login':            (_) => const LoginScreen(),
            '/onboarding':       (_) => const PostLoginGate(),
            '/chat-persona':     (_) => const ChatPersonaScreen(),
            '/relax-audio':      (_) => const RelaxAudioScreen(),
            '/guided-sessions':  (_) => const GuidedSessionsScreen(),
            '/settings':         (_) => const SettingsScreen(),
            '/paywall':          (_) => const PaywallScreen(),
            '/voice-chat':       (_) => const VoiceChatScreen(),
            '/sos':              (_) => const SosScreen(),
            '/disclaimer':       (_) => const DisclaimerScreen(),
            '/blog':             (_) => const BlogScreen(),
            '/journey':          (_) => const JourneyScreen(),
            '/wins':             (_) => const WinsScreen(),
            '/truth-deck':       (_) => const TruthDeckScreen(),
            // Sleep Ritual — reads mode from route arguments
            '/sleep-ritual': (ctx) {
              final args = ModalRoute.of(ctx)?.settings.arguments;
              SleepRitualMode mode = SleepRitualMode.evening;
              if (args is Map) {
                final m = args['mode']?.toString() ?? 'evening';
                mode = m == 'morning' ? SleepRitualMode.morning : SleepRitualMode.evening;
              }
              return SleepRitualScreen(mode: mode);
            },
          },
          home: StreamBuilder<User?>(
            stream: FirebaseAuth.instance.authStateChanges(),
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Scaffold(body: Center(child: CircularProgressIndicator()));
              }
              return snap.data == null ? const LoginScreen() : const PostLoginGate();
            },
          ),
        );
      },
    );
  }
}
