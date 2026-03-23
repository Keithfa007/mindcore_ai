import 'package:flutter/material.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';

class SupportPromptChip {
  final String label;
  final String promptText;
  final IconData icon;
  final bool autoSend;
  final String? routeName;
  final Map<String, dynamic>? routeArguments;

  const SupportPromptChip({
    required this.label,
    required this.promptText,
    required this.icon,
    this.autoSend = false,
    this.routeName,
    this.routeArguments,
  });
}

enum RecommendationType {
  chat,
  breathe,
  reset,
  journal,
  audio,
}

class ProactiveSuggestion {
  final String id;
  final RecommendationType type;
  final String title;
  final String subtitle;
  final String ctaLabel;
  final String routeName;
  final IconData icon;
  final String notificationTitle;
  final String notificationBody;
  final Map<String, dynamic>? routeArguments;

  const ProactiveSuggestion({
    required this.id,
    required this.type,
    required this.title,
    required this.subtitle,
    required this.ctaLabel,
    required this.routeName,
    required this.icon,
    required this.notificationTitle,
    required this.notificationBody,
    this.routeArguments,
  });

  SupportPromptChip toPromptChip() {
    if (type == RecommendationType.chat) {
      final prefill = (routeArguments?['prefillText'] ?? title).toString();
      final autoSend = routeArguments?['autoSend'] == true;
      return SupportPromptChip(
        label: ctaLabel,
        promptText: prefill,
        icon: icon,
        autoSend: autoSend,
      );
    }

    return SupportPromptChip(
      label: ctaLabel,
      promptText: '',
      icon: icon,
      routeName: routeName,
      routeArguments: routeArguments,
    );
  }
}

class ProactiveSupportService {
  static Future<ProactiveSuggestion> buildHomeSuggestion() async {
    final moods = await MoodRepo.instance.last7Normalized();
    final journals = await JournalService.getEntries();
    final now = DateTime.now();
    final avgMood = moods.isEmpty ? 0.0 : moods.reduce((a, b) => a + b) / moods.length;
    final latestJournal = journals.isEmpty ? '' : journals.first.note.toLowerCase();

    if (now.hour >= 20) {
      return const ProactiveSuggestion(
        id: 'evening_audio_wind_down',
        type: RecommendationType.audio,
        title: 'Wind down with relaxing audio',
        subtitle: 'Your evening recommendation is a gentle audio session to help your body and mind slow down.',
        ctaLabel: 'Open audio',
        routeName: '/relax-audio',
        icon: Icons.nights_stay_rounded,
        notificationTitle: 'Your evening recommendation is ready',
        notificationBody: 'Open MindCore AI for a calming audio session to help you unwind tonight.',
        routeArguments: {
          'trackTitle': 'Evening Wind Down',
          'autoplay': true,
          'source': 'recommendation',
        },
      );
    }

    if (latestJournal.contains('sleep') || latestJournal.contains('tired') || latestJournal.contains('exhaust')) {
      return const ProactiveSuggestion(
        id: 'sleep_audio_transition',
        type: RecommendationType.audio,
        title: 'Support your energy gently',
        subtitle: 'Your recent notes suggest low energy. A softer audio or reset could help more than pushing harder.',
        ctaLabel: 'Open audio',
        routeName: '/relax-audio',
        icon: Icons.bedtime_rounded,
        notificationTitle: 'A gentler recommendation is ready',
        notificationBody: "Today's recommendation is a softer reset to support your energy and help you recover.",
        routeArguments: {
          'trackTitle': 'Sleep Transition Session',
          'autoplay': true,
          'source': 'recommendation',
        },
      );
    }

    if (avgMood > 0.0 && avgMood <= 0.45) {
      return const ProactiveSuggestion(
        id: 'low_mood_reset',
        type: RecommendationType.reset,
        title: 'Start with one calming step',
        subtitle: 'Your recent mood trend looks a bit heavy. A short reset or grounding audio could help lighten the pressure.',
        ctaLabel: 'Open reset',
        routeName: '/reset',
        icon: Icons.spa_outlined,
        notificationTitle: 'A calm reset is ready for you',
        notificationBody: 'Open MindCore AI for a short grounding reset and one steady next step.',
        routeArguments: {
          'source': 'recommendation',
        },
      );
    }

    if (latestJournal.contains('stress') || latestJournal.contains('overwhelm') || latestJournal.contains('work') || latestJournal.contains('anx')) {
      return const ProactiveSuggestion(
        id: 'stress_chat_checkin',
        type: RecommendationType.chat,
        title: 'Clear the mental clutter',
        subtitle: 'A quick check-in in chat could help you turn pressure into something simpler and more manageable.',
        ctaLabel: 'Open chat',
        routeName: '/chat',
        icon: Icons.psychology_alt_outlined,
        notificationTitle: 'Your check-in is ready',
        notificationBody: 'Open MindCore AI for a short guided check-in and a calmer plan for today.',
        routeArguments: {
          'prefillText': 'I feel mentally cluttered and a bit pressured. Please help me do a calm check-in and turn this into one simple plan.',
          'autoSend': false,
          'source': 'recommendation',
        },
      );
    }

    if (now.hour < 11) {
      return const ProactiveSuggestion(
        id: 'morning_chat_checkin',
        type: RecommendationType.chat,
        title: 'Set a steady tone for today',
        subtitle: 'A calm morning check-in can help the rest of the day feel clearer, lighter, and more intentional.',
        ctaLabel: 'Start chat',
        routeName: '/chat',
        icon: Icons.wb_sunny_outlined,
        notificationTitle: 'Your morning recommendation is ready',
        notificationBody: 'Open MindCore AI for a calm check-in to start your day with more clarity.',
        routeArguments: {
          'prefillText': 'Help me do a calm morning check-in and set one realistic intention for today.',
          'autoSend': false,
          'source': 'recommendation',
        },
      );
    }

    return const ProactiveSuggestion(
      id: 'default_journal_reflection',
      type: RecommendationType.journal,
      title: 'Keep your momentum gentle',
      subtitle: 'You do not need to do everything at once. One helpful step is enough right now.',
      ctaLabel: 'Open journal',
      routeName: '/daily-hub',
      icon: Icons.auto_awesome_outlined,
      notificationTitle: 'A small helpful step is ready',
      notificationBody: "Open MindCore AI for today's recommendation and one gentle next action.",
      routeArguments: {
        'source': 'recommendation',
      },
    );
  }

  static List<SupportPromptChip> buildChatPromptChips({
    required String moodLabel,
    required bool isEvening,
    required bool hasMessages,
    ProactiveSuggestion? unifiedSuggestion,
  }) {
    final mood = moodLabel.toLowerCase();
    final chips = <SupportPromptChip>[];

    if (unifiedSuggestion != null) {
      chips.add(unifiedSuggestion.toPromptChip());
    }

    if (!hasMessages) {
      if (mood.contains('anx') || mood.contains('stress') || mood.contains('panic')) {
        chips.addAll(const [
          SupportPromptChip(
            label: 'Calm me down',
            promptText: 'I feel anxious right now. Please help me calm down with one simple step.',
            icon: Icons.spa_outlined,
            autoSend: true,
          ),
          SupportPromptChip(
            label: 'Sort my thoughts',
            promptText: 'My mind feels cluttered. Help me sort my thoughts into something simpler.',
            icon: Icons.tune_rounded,
            autoSend: true,
          ),
        ]);
      } else if (isEvening) {
        chips.addAll(const [
          SupportPromptChip(
            label: 'Wind down',
            promptText: 'Help me wind down for the evening and slow my thoughts a bit.',
            icon: Icons.nights_stay_rounded,
            autoSend: true,
          ),
          SupportPromptChip(
            label: 'Sleep support',
            promptText: 'I want help switching off for sleep tonight.',
            icon: Icons.bedtime_rounded,
            autoSend: true,
          ),
        ]);
      }
    }

    if (chips.length < 3) {
      chips.addAll(const [
        SupportPromptChip(
          label: 'Quick check-in',
          promptText: 'Can we do a quick emotional check-in for how I am doing today?',
          icon: Icons.favorite_border,
          autoSend: true,
        ),
        SupportPromptChip(
          label: 'Mental reset',
          promptText: 'I need a quick mental reset. Keep it calm and practical.',
          icon: Icons.refresh_rounded,
          autoSend: true,
        ),
        SupportPromptChip(
          label: 'Small plan',
          promptText: 'Help me create a small realistic plan for the next part of my day.',
          icon: Icons.checklist_rounded,
          autoSend: true,
        ),
      ]);
    }

    final deduped = <String>{};
    return chips.where((chip) => deduped.add(chip.label)).take(3).toList();
  }
}
