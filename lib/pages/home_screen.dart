import 'package:flutter/material.dart';
import '../widgets/page_scaffold.dart';
import '../widgets/surfaces.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';

import 'package:mindcore_ai/pages/chat_screen.dart';
import 'package:mindcore_ai/pages/helpers/journal_service.dart';

import 'package:mindcore_ai/services/daily_plan_service.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';
import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';
import 'package:mindcore_ai/widgets/tts_replay_button.dart';
import 'package:mindcore_ai/widgets/tts_speaker_button.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with AutoStopTtsRouteAware<HomeScreen> {
  final TextEditingController _plan = TextEditingController();
  bool _savingPlan = false;

  List<double> _last7 = const [];
  ProactiveSuggestion? _supportSuggestion;

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  @override
  void dispose() {
    _plan.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  Future<void> _loadAll() async {
    await DailyPlanService.getTodayNote();
    final mood = await MoodRepo.instance.last7Normalized();
    final suggestion = await ProactiveSupportService.buildHomeSuggestion();
    final reminderEnabled = await SettingsService.getDailyReminderEnabled();
    final reminderTime = await SettingsService.getDailyReminderTime();

    if (reminderEnabled) {
      await NotificationService.instance.scheduleDailyRecommendationNotification(
        uniqueKey: suggestion.id,
        title: suggestion.notificationTitle,
        body: suggestion.notificationBody,
        routeName: suggestion.routeName,
        routeArguments: suggestion.routeArguments,
        hour: reminderTime.hour,
        minute: reminderTime.minute,
      );
    }

    if (!mounted) return;

    setState(() {
      _plan.text = '';
      _last7 = mood;
      _supportSuggestion = suggestion;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      final autoSpeakText = suggestion.subtitle.trim().isNotEmpty
          ? '${suggestion.title}. ${suggestion.subtitle.split('.').first.trim()}'
          : suggestion.title;
      await OpenAiTtsService.instance.maybeSpeakOncePerDay(
        uniqueKey: suggestion.id,
        text: autoSpeakText,
        surface: TtsSurface.recommendation,
        moodLabel: 'calm',
        messageId: 'home_recommendation_${suggestion.id}',
      );
    });
  }

  Future<void> _saveJournal() async {
    final text = _plan.text.trim();
    if (_savingPlan) return;

    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Write something first.')),
      );
      return;
    }

    setState(() => _savingPlan = true);
    await JournalService.addEntry(text, when: DateTime.now());

    if (!mounted) return;

    setState(() => _savingPlan = false);
    _plan.clear();
    FocusScope.of(context).unfocus();

    await _loadAll();

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Journal entry saved.')),
    );
  }

  void _openRecommendation() {
    final suggestion = _supportSuggestion;
    if (suggestion == null) return;
    Navigator.of(context).pushNamed(
      suggestion.routeName,
      arguments: suggestion.routeArguments,
    );
  }

  Future<void> _speakRecommendation() async {
    final suggestion = _supportSuggestion;
    if (suggestion == null) return;
    await OpenAiTtsService.instance.speak(
      '${suggestion.title}. ${suggestion.subtitle}',
      moodLabel: 'calm',
      surface: TtsSurface.recommendation,
      messageId: 'speak_recommendation_${suggestion.id}',
      force: true,
    );
  }

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      title: 'MindCore AI',
      bottomIndex: 0,
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          children: [
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(
                    title: 'Daily Reset',
                    subtitle: 'A quick moment to breathe and recenter',
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () => Navigator.of(context).pushNamed('/reset'),
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(54),
                      ),
                      child: const Text(
                        'Quick Reset',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    '60 seconds to calm your mind.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.black.withValues(alpha: 0.75),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            GradientButton.primary(
              'Start Chat',
              onPressed: () {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const ChatScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(
                    title: 'Guided Sessions',
                    subtitle: 'Ready-to-play calming audio journeys for focus, sleep, panic, and emotional reset',
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () => Navigator.of(context).pushNamed('/guided-sessions'),
                      icon: const Icon(Icons.self_improvement_rounded),
                      label: const Text('Open Guided Sessions'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (_supportSuggestion != null)
              GlassCard(
                padding: const EdgeInsets.all(18),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionHeroCard(
                      title: 'Recommended for you',
                      subtitle: 'A gentle nudge based on your recent activity',
                    ),
                    const SizedBox(height: 12),
                    NestCard(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(_supportSuggestion!.icon, size: 22),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  _supportSuggestion!.title,
                                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(_supportSuggestion!.subtitle),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: _openRecommendation,
                            icon: Icon(_supportSuggestion!.icon, size: 18),
                            label: Text(_supportSuggestion!.ctaLabel),
                          ),
                        ),
                        const SizedBox(width: 10),
                        TtsSpeakerButton(
                          text: '${_supportSuggestion!.title}. ${_supportSuggestion!.subtitle}',
                          surface: TtsSurface.recommendation,
                          moodLabel: 'calm',
                          messageId: 'speak_recommendation_${_supportSuggestion!.id}',
                        ),
                        const SizedBox(width: 8),
                        const TtsReplayButton(surface: TtsSurface.recommendation),
                      ],
                    ),
                  ],
                ),
              ),
            if (_supportSuggestion != null) const SizedBox(height: 12),
            GlassCard(
              padding: const EdgeInsets.all(18),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(
                    title: 'Journal',
                    subtitle: 'You can write anything here.',
                  ),
                  const SizedBox(height: 12),
                  NestCard(
                    child: TextField(
                      controller: _plan,
                      maxLines: 4,
                      textInputAction: TextInputAction.newline,
                      decoration: const InputDecoration(
                        hintText: 'A few lines is enough…',
                        border: InputBorder.none,
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton(
                          onPressed: _savingPlan ? null : _saveJournal,
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 12.0),
                            child: Text(_savingPlan ? 'Saving…' : 'Save entry'),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      OutlinedButton(
                        onPressed: () => Navigator.of(context).pushNamed('/daily-hub'),
                        child: const Padding(
                          padding: EdgeInsets.symmetric(vertical: 12.0),
                          child: Text('View'),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Saved locally on your device.',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white.withValues(alpha: 0.65),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
