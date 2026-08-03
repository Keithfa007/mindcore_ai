// lib/main.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
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
import 'pages/pressure_valve_screen.dart';
import 'pages/habit_mindscore_screen.dart';

import 'pages/helpers/route_observer.dart';
import 'services/settings_service.dart';
import 'services/notification_service.dart';
import 'services/openai_tts_service.dart';
import 'services/premium_service.dart';
import 'services/usage_service.dart';
import 'widgets/animated_backdrop.dart';
import 'widgets/animated_logo.dart';

final GlobalKey<NavigatorState> appNavigatorKey = GlobalKey<NavigatorState>();

/// Flips to true once all startup services have finished initializing.
/// While false, the app shows the animated splash instead of a flat screen.
final ValueNotifier<bool> _bootReady = ValueNotifier<bool>(false);

@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Only the minimum needed before the first frame, so the animated splash
  // appears fast instead of the flat native launch screen.
  await Firebase.initializeApp();
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);

  runApp(const MindCoreApp());

  // Everything else initializes behind the animated splash.
  _bootstrap();
}

/// Heavy startup work, run after the first frame so the UI is never blank/flat.
Future<void> _bootstrap() async {
  try {
    await SettingsService.init();
    await SystemChrome.setPreferredOrientations([
      DeviceOrientation.portraitUp,
      DeviceOrientation.portraitDown,
    ]);
    await OpenAiTtsService.instance.init();

    final messaging = FirebaseMessaging.instance;
    // Do NOT await: let the OS permission prompt float over the app rather
    // than block startup behind it.
    messaging.requestPermission(alert: true, badge: true, sound: true);
    messaging.subscribeToTopic('relax_audio_updates');
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      final screen = message.data['screen'];
      if (screen == 'relax_audio') {
        appNavigatorKey.currentState?.pushNamed('/relax-audio');
      }
    });
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      final screen = message.data['screen'];
      if (screen == 'relax_audio') {
        appNavigatorKey.currentState?.pushNamed('/relax-audio');
      }
    });

    await PremiumService.init();
    await UsageService.instance.init();
    await NotificationService.instance.init(navigatorKey: appNavigatorKey);
  } catch (e) {
    debugPrint('Bootstrap error: $e');
  } finally {
    _bootReady.value = true;
  }
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
            '/pressure-valve':   (_) => const PressureValveScreen(),
            '/mindscore':        (_) => const HabitMindScoreScreen(),
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
          home: ValueListenableBuilder<bool>(
            valueListenable: _bootReady,
            builder: (context, ready, _) {
              if (!ready) return const AnimatedSplashScreen();
              return StreamBuilder<User?>(
                stream: FirebaseAuth.instance.authStateChanges(),
                builder: (context, snap) {
                  if (snap.connectionState == ConnectionState.waiting) {
                    return const AnimatedSplashScreen();
                  }
                  return snap.data == null
                      ? const LoginScreen()
                      : const PostLoginGate();
                },
              );
            },
          ),
        );
      },
    );
  }
}

/// Animated branded splash: the breathing / glowing logo on the aurora
/// backdrop, shown while the app boots instead of the flat native screen.
class AnimatedSplashScreen extends StatelessWidget {
  const AnimatedSplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const AnimatedLogo(size: 150),
              const SizedBox(height: 28),
              Text(
                'MindCore AI',
                style: tt.headlineSmall?.copyWith(
                  fontWeight: FontWeight.w900,
                  letterSpacing: -0.8,
                  color: isDark ? Colors.white : const Color(0xFF0E1320),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                'Getting things ready…',
                style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.45)
                      : Colors.black.withValues(alpha: 0.45),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
