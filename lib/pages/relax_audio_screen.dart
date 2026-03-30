// lib/pages/relax_audio_screen.dart
import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';

import '../widgets/page_scaffold.dart';
import '../widgets/surfaces.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';
import 'package:mindcore_ai/services/relax_audio_engine.dart';
import 'package:mindcore_ai/services/premium_service.dart';

class RelaxTrack {
  final String id;
  final String title;
  final String subtitle;
  final String assetPath;

  const RelaxTrack({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.assetPath,
  });
}

class RelaxAudioScreen extends StatefulWidget {
  const RelaxAudioScreen({super.key});

  @override
  State<RelaxAudioScreen> createState() => _RelaxAudioScreenState();
}

class _RelaxAudioScreenState extends State<RelaxAudioScreen>
    with AutoStopTtsRouteAware<RelaxAudioScreen> {
  final AudioPlayer _player = AudioPlayer();
  int? _currentIndex;
  bool _isPlaying = false;
  bool _didHandleRouteArgs = false;
  String? _recommendedTrackTitle;
  String? _recommendedTrackSubtitle;
  String? _recommendedFrequencyLabel;

  final List<RelaxTrack> _tracks = const [
    RelaxTrack(
      id: 'body_scan_emotional_tension',
      title: 'Body Scan for Emotional Tension',
      subtitle: 'Release tension gently from head to toe.',
      assetPath: 'audio/Body Scan for Emotional Tension.mp3',
    ),
    RelaxTrack(
      id: 'calm_breathing_reset',
      title: 'Calm Breathing Reset',
      subtitle: 'Slow, guided breathing to reset your nervous system.',
      assetPath: 'audio/calmbreathingreset.mp3',
    ),
    RelaxTrack(
      id: 'confidence_grounding',
      title: 'Confidence Grounding',
      subtitle: 'Drop into your body and reconnect with inner strength.',
      assetPath: 'audio/Confidence Grounding.mp3',
    ),
    RelaxTrack(
      id: 'digital_detox_reset',
      title: 'Digital Detox Reset',
      subtitle: 'Step away from screens and clear mental overload.',
      assetPath: 'audio/Digital Detox Reset.mp3',
    ),
    RelaxTrack(
      id: 'empowering_affirmations',
      title: 'Empowering Affirmations',
      subtitle: 'Positive statements to rebuild self-belief.',
      assetPath: 'audio/Empowering Affirmations.mp3',
    ),
    RelaxTrack(
      id: 'evening_wind_down',
      title: 'Evening Wind Down',
      subtitle: 'Let go of the day and prepare for deep rest.',
      assetPath: 'audio/Evening Wind Down.mp3',
    ),
    RelaxTrack(
      id: 'gratitude_moment',
      title: 'Gratitude Moment',
      subtitle: 'Shift into appreciation and calm perspective.',
      assetPath: 'audio/Gratitude Moment.mp3',
    ),
    RelaxTrack(
      id: 'grief_soother',
      title: 'Grief Soother',
      subtitle: 'Gentle support for heavy, grieving moments.',
      assetPath: 'audio/Grief Soother.mp3',
    ),
    RelaxTrack(
      id: 'morning_mind_reset',
      title: 'Morning Mind Reset',
      subtitle: 'Start your day clear, calm and focused.',
      assetPath: 'audio/Morning Mind Reset.mp3',
    ),
    RelaxTrack(
      id: 'morning_motivation_boost',
      title: 'Morning Motivation Boost',
      subtitle: 'Light a fire under your goals with calm energy.',
      assetPath: 'audio/Morning Motivation Boost.mp3',
    ),
    RelaxTrack(
      id: 'overthinking_reset',
      title: 'Overthinking Reset',
      subtitle: 'Step out of your head and back into the present.',
      assetPath: 'audio/Overthinking Reset.mp3',
    ),
    RelaxTrack(
      id: 'panic_calmer',
      title: 'Panic Calmer',
      subtitle: 'Short grounding track for intense anxiety spikes.',
      assetPath: 'audio/Panic Calmer.mp3',
    ),
    RelaxTrack(
      id: 'reset_after_conflict',
      title: 'Reset After Conflict',
      subtitle: 'Settle your body and mind after arguments or tension.',
      assetPath: 'audio/Reset After Conflict.mp3',
    ),
    RelaxTrack(
      id: 'self_compassion_moment',
      title: 'Self-Compassion Moment',
      subtitle: 'Practice kindness with yourself when you feel low.',
      assetPath: 'audio/Self Compassion Moment.mp3',
    ),
    RelaxTrack(
      id: 'self_compassion',
      title: 'Self-Compassion',
      subtitle: 'Deeper self-compassion practice for emotional healing.',
      assetPath: 'audio/Self Compassion.mp3',
    ),
    RelaxTrack(
      id: 'sleep_transition_session',
      title: 'Sleep Transition Session',
      subtitle: 'Drift from alertness into sleep-ready calm.',
      assetPath: 'audio/Sleep Transition Session.mp3',
    ),
    RelaxTrack(
      id: 'social_overwhelm_reset',
      title: 'Social Overwhelm Reset',
      subtitle: 'Come down gently after intense social situations.',
      assetPath: 'audio/Sociall Overwhelm Reset.mp3',
    ),
    RelaxTrack(
      id: 'stress_cleanse',
      title: 'Stress Cleanse',
      subtitle: 'Flush out built-up stress and reboot your system.',
      assetPath: 'audio/Stress Cleanse.mp3',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _checkPremiumAccess();
    _player.setReleaseMode(ReleaseMode.stop);
    _player.onPlayerComplete.listen((_) {
      if (!mounted) return;
      setState(() => _isPlaying = false);
    });
  }

  // ✅ Premium gate: if not premium, show paywall then pop if still not premium.
  Future<void> _checkPremiumAccess() async {
    await Future.delayed(const Duration(milliseconds: 250));
    if (!mounted) return;
    if (!PremiumService.isPremium.value) {
      await Navigator.of(context).pushNamed('/paywall');
      // Only pop if user did not subscribe during the paywall session.
      if (mounted && !PremiumService.isPremium.value) {
        Navigator.of(context).pop();
      }
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didHandleRouteArgs) return;
    _didHandleRouteArgs = true;

    final args = ModalRoute.of(context)?.settings.arguments;
    if (args is! Map) return;

    final trackId = args['trackId']?.toString();
    final trackTitle = args['trackTitle']?.toString();
    final moodLabel = args['moodLabel']?.toString();
    final autoplay = args['autoplay'] == true;

    int index = -1;
    RelaxAudioRecommendation? recommendation;

    if (trackId != null && trackId.isNotEmpty) {
      index = _tracks.indexWhere((t) => t.id == trackId);
    }
    if (index == -1 && trackTitle != null && trackTitle.isNotEmpty) {
      index = _tracks.indexWhere(
        (t) => t.title.toLowerCase() == trackTitle.toLowerCase(),
      );
    }
    if (index == -1 && moodLabel != null && moodLabel.trim().isNotEmpty) {
      recommendation = RelaxAudioEngine.recommend(moodLabel: moodLabel);
      index = _tracks.indexWhere(
        (t) => t.title.toLowerCase() == recommendation!.title.toLowerCase(),
      );
    }
    if (index == -1) return;

    recommendation ??= RelaxAudioEngine.recommend(
      moodLabel: moodLabel?.trim().isNotEmpty == true
          ? moodLabel!
          : _tracks[index].title,
    );

    _recommendedTrackTitle = _tracks[index].title;
    _recommendedTrackSubtitle = recommendation.subtitle;
    _recommendedFrequencyLabel = recommendation.frequencyLabel;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted) return;
      setState(() => _currentIndex = index);
      if (autoplay) {
        await _playTrack(index);
      }
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _playTrack(int index) async {
    final track = _tracks[index];
    try {
      await _player.stop();
      await _player.play(AssetSource(track.assetPath));
      if (!mounted) return;
      setState(() {
        _currentIndex = index;
        _isPlaying = true;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not play audio: $e')),
      );
    }
  }

  Future<void> _toggleTrack(int index) async {
    if (_currentIndex == index) {
      if (_isPlaying) {
        await _player.pause();
        if (!mounted) return;
        setState(() => _isPlaying = false);
      } else {
        await _player.resume();
        if (!mounted) return;
        setState(() => _isPlaying = true);
      }
      return;
    }
    await _playTrack(index);
  }

  Future<void> _stopTrack(int index) async {
    if (_currentIndex != index) return;
    await _player.stop();
    if (!mounted) return;
    setState(() {
      _isPlaying = false;
      _currentIndex = null;
    });
  }

  Future<void> _stopAll() async {
    await _player.stop();
    if (!mounted) return;
    setState(() {
      _isPlaying = false;
      _currentIndex = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return PageScaffold(
      title: 'Relaxing Audio',
      bottomIndex: 4,
      body: AnimatedBackdrop(
        child: SafeArea(
          top: false,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
            children: [
              GlassCard(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Reset with sound',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Choose a session, press play, and let it run while you breathe, journal, or simply rest.',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: cs.onSurface.withValues(alpha: 0.7),
                          ),
                    ),
                    if (_recommendedTrackTitle != null) ...[
                      const SizedBox(height: 10),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: cs.primary.withValues(alpha: 0.08),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          'Recommended: $_recommendedTrackTitle',
                          style:
                              Theme.of(context).textTheme.labelMedium?.copyWith(
                                    color: cs.primary,
                                    fontWeight: FontWeight.w700,
                                  ),
                        ),
                      ),
                      if (_recommendedFrequencyLabel != null ||
                          _recommendedTrackSubtitle != null) ...[
                        const SizedBox(height: 10),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: cs.surface,
                            borderRadius: BorderRadius.circular(16),
                            border: Border.all(
                              color: cs.outlineVariant.withValues(alpha: 0.35),
                            ),
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              if (_recommendedFrequencyLabel != null)
                                Text(
                                  _recommendedFrequencyLabel!,
                                  style: Theme.of(context)
                                      .textTheme
                                      .labelLarge
                                      ?.copyWith(
                                        color: cs.primary,
                                        fontWeight: FontWeight.w800,
                                      ),
                                ),
                              if (_recommendedTrackSubtitle != null) ...[
                                const SizedBox(height: 4),
                                Text(
                                  _recommendedTrackSubtitle!,
                                  style: Theme.of(context)
                                      .textTheme
                                      .bodySmall
                                      ?.copyWith(
                                        color: cs.onSurface.withValues(
                                          alpha: 0.72,
                                        ),
                                      ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ],
                    const SizedBox(height: 10),
                    if (_currentIndex != null)
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton.icon(
                          onPressed: _stopAll,
                          icon: const Icon(Icons.stop_circle_outlined),
                          label: const Text('Stop all'),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              for (int i = 0; i < _tracks.length; i++) ...[
                _AudioTrackTile(
                  track: _tracks[i],
                  isRecommended: _tracks[i].title == _recommendedTrackTitle,
                  isActive: _currentIndex == i,
                  isPlaying: _currentIndex == i && _isPlaying,
                  onPlayPause: () => _toggleTrack(i),
                  onStop: () => _stopTrack(i),
                ),
                const SizedBox(height: 10),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _AudioTrackTile extends StatelessWidget {
  final RelaxTrack track;
  final bool isRecommended;
  final bool isActive;
  final bool isPlaying;
  final VoidCallback onPlayPause;
  final VoidCallback onStop;

  const _AudioTrackTile({
    required this.track,
    required this.isRecommended,
    required this.isActive,
    required this.isPlaying,
    required this.onPlayPause,
    required this.onStop,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    return SurfaceCard(
      padding: EdgeInsets.zero,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 220),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: isActive
                ? cs.primary.withValues(alpha: 0.35)
                : cs.outlineVariant.withValues(alpha: 0.14),
          ),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isActive
                ? [
                    cs.primary.withValues(alpha: 0.11),
                    cs.surface.withValues(alpha: 0.96),
                  ]
                : [
                    cs.surface.withValues(alpha: 0.96),
                    cs.surface.withValues(alpha: 0.90),
                  ],
          ),
          boxShadow: [
            BoxShadow(
              color: isActive
                  ? cs.primary.withValues(alpha: 0.12)
                  : Colors.black.withValues(alpha: 0.04),
              blurRadius: isActive ? 24 : 16,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 14),
          child: Row(
            children: [
              _MediaControlButton(
                isActive: isActive,
                isPlaying: isPlaying,
                onTap: onPlayPause,
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            track.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.titleMedium?.copyWith(
                              fontWeight:
                                  isActive ? FontWeight.w800 : FontWeight.w700,
                              height: 1.15,
                            ),
                          ),
                        ),
                        if (isRecommended) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: cs.primary.withValues(alpha: 0.09),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              'For you',
                              style: theme.textTheme.labelSmall?.copyWith(
                                color: cs.primary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      track.subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: cs.onSurface.withValues(alpha: 0.62),
                        height: 1.22,
                      ),
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 10,
                            vertical: 5,
                          ),
                          decoration: BoxDecoration(
                            color: isActive
                                ? cs.primary.withValues(alpha: 0.10)
                                : cs.surfaceContainerHighest.withValues(
                                    alpha: 0.65,
                                  ),
                            borderRadius: BorderRadius.circular(999),
                          ),
                          child: Text(
                            isActive
                                ? (isPlaying ? 'Now playing' : 'Paused')
                                : 'Ready',
                            style: theme.textTheme.labelSmall?.copyWith(
                              color: isActive
                                  ? cs.primary
                                  : cs.onSurface.withValues(alpha: 0.62),
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                        const Spacer(),
                        if (isActive)
                          IconButton(
                            onPressed: onStop,
                            tooltip: 'Stop',
                            icon: const Icon(Icons.stop_rounded),
                            style: IconButton.styleFrom(
                              backgroundColor:
                                  cs.surface.withValues(alpha: 0.75),
                              foregroundColor: cs.onSurface,
                              side: BorderSide(
                                color:
                                    cs.outlineVariant.withValues(alpha: 0.24),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MediaControlButton extends StatelessWidget {
  final bool isActive;
  final bool isPlaying;
  final VoidCallback onTap;

  const _MediaControlButton({
    required this.isActive,
    required this.isPlaying,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 220),
          width: 62,
          height: 62,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: isActive
                  ? const [Color(0xFF5C8EFF), Color(0xFF78C9FF)]
                  : [
                      cs.surfaceContainerHighest.withValues(alpha: 0.92),
                      cs.surfaceContainer.withValues(alpha: 0.96),
                    ],
            ),
            boxShadow: [
              BoxShadow(
                color: isActive
                    ? const Color(0xFF5C8EFF).withValues(alpha: 0.24)
                    : Colors.black.withValues(alpha: 0.05),
                blurRadius: isActive ? 24 : 14,
                offset: const Offset(0, 8),
              ),
            ],
            border: Border.all(
              color: isActive
                  ? Colors.white.withValues(alpha: 0.18)
                  : cs.outlineVariant.withValues(alpha: 0.16),
            ),
          ),
          child: Icon(
            isPlaying ? Icons.pause_rounded : Icons.play_arrow_rounded,
            size: 30,
            color:
                isActive ? Colors.white : cs.onSurface.withValues(alpha: 0.72),
          ),
        ),
      ),
    );
  }
}
