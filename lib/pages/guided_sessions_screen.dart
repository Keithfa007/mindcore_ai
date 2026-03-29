import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/ai_guided_session_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/widgets/ai_speaking_wave.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';
import 'package:mindcore_ai/widgets/tts_speaker_button.dart';

class GuidedSessionsScreen extends StatefulWidget {
  const GuidedSessionsScreen({super.key});

  @override
  State<GuidedSessionsScreen> createState() => _GuidedSessionsScreenState();
}

class _GuidedSessionsScreenState extends State<GuidedSessionsScreen> {
  String _selectedCategory = AiGuidedSessionService.categories().first;

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
  }

  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      if (mounted) Navigator.of(context).pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    final plans = AiGuidedSessionService.byCategory(_selectedCategory);
    final recommended =
        AiGuidedSessionService.recommendForMood(_selectedCategory);

    return PageScaffold(
      title: 'AI Guided Sessions',
      bottomIndex: 4,
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
          children: [
            GlassCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SectionHeroCard(
                    title: 'AI Guided Sessions',
                    subtitle:
                        'Choose a calming path and launch a guided reset matched to what you need right now.',
                  ),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Recommended now: ${recommended.title}',
                          style: Theme.of(context)
                              .textTheme
                              .titleSmall
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                      ),
                      AnimatedBuilder(
                        animation: OpenAiTtsService.instance,
                        builder: (context, _) => AiSpeakingWave(
                          active: OpenAiTtsService.instance.isSpeakingNow,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(recommended.subtitle),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children:
                        AiGuidedSessionService.categories().map((category) {
                      final selected = category == _selectedCategory;
                      return ChoiceChip(
                        selected: selected,
                        label: Text(category),
                        onSelected: (_) =>
                            setState(() => _selectedCategory = category),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            for (final plan in plans) ...[
              GlassCard(child: _SessionPlanCard(plan: plan)),
              const SizedBox(height: 12),
            ],
          ],
        ),
      ),
    );
  }
}

class _SessionPlanCard extends StatelessWidget {
  final AiGuidedSessionPlan plan;
  const _SessionPlanCard({required this.plan});

  @override
  Widget build(BuildContext context) {
    final track = plan.track;
    final intro = AiGuidedSessionService.spokenIntro(plan);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    plan.title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  const SizedBox(height: 6),
                  Text(plan.subtitle),
                ],
              ),
            ),
            const SizedBox(width: 8),
            TtsSpeakerButton(
              text: intro,
              surface: TtsSurface.reflection,
              moodLabel: plan.moodHint,
              messageId: 'guided_intro_${plan.id}',
            ),
          ],
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _InfoChip(label: '${plan.minutes} min'),
            _InfoChip(label: plan.category),
            _InfoChip(label: 'Mood: ${plan.moodHint}'),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          'Flow',
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        for (int i = 0; i < plan.steps.length; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 24,
                  height: 24,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: Theme.of(context)
                        .colorScheme
                        .primary
                        .withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text('${i + 1}'),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text(plan.steps[i])),
              ],
            ),
          ),
        const SizedBox(height: 4),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                icon: const Icon(Icons.self_improvement_rounded),
                label: const Text('Open breathing coach'),
                onPressed: () =>
                    Navigator.of(context).pushNamed('/breathe'),
              ),
            ),
          ],
        ),
        if (track != null) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.play_circle_fill_rounded),
                  label: Text('Play ${track.title}'),
                  onPressed: () {
                    Navigator.of(context).pushNamed(
                      '/relax-audio',
                      arguments: {
                        'trackId': track.id,
                        'autoplay': true,
                      },
                    );
                  },
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}

class _InfoChip extends StatelessWidget {
  final String label;
  const _InfoChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: Theme.of(context)
              .colorScheme
              .outlineVariant
              .withValues(alpha: 0.30),
        ),
      ),
      child: Text(label),
    );
  }
}