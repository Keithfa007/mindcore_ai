// lib/pages/settings_screen.dart
import 'package:flutter/material.dart';

import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';

import 'package:mindcore_ai/pages/voice_settings_screen.dart';
import 'package:mindcore_ai/pages/chat_persona_screen.dart';
import 'package:mindcore_ai/pages/safety_screen.dart';
import 'package:mindcore_ai/pages/privacy_controls_screen.dart';

// Shared UI (MindReset look)
import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/section_hero_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  // Breathe
  BreathePreset _preset = BreathePreset.box;
  int _duration = 60;
  bool _haptics = true;
  final _durations = const [30, 60, 90, 180];

  // Reminders
  bool _dailyReminderEnabled = false;
  TimeOfDay _dailyReminderTime = const TimeOfDay(hour: 8, minute: 0);

  // Voice / TTS
  bool _ttsEnabled = true;
  bool _moodAdaptiveVoice = true;

  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final preset = await SettingsService.getPreset();
      final duration = await SettingsService.getDurationSecs();
      final haptics = await SettingsService.getHaptics();
      final dailyEnabled = await SettingsService.getDailyReminderEnabled();
      final dailyTime = await SettingsService.getDailyReminderTime();

      final ttsEnabled = await OpenAiTtsService.instance.getEnabled();
      final moodAdaptive = await OpenAiTtsService.instance.getMoodAdaptive();

      if (!mounted) return;
      setState(() {
        _preset = preset;
        _duration = duration;
        _haptics = haptics;
        _dailyReminderEnabled = dailyEnabled;
        _dailyReminderTime = dailyTime;

        _ttsEnabled = ttsEnabled;
        _moodAdaptiveVoice = moodAdaptive;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to load settings: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _clearData() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear local data?'),
        content: const Text(
          'This will remove local journal/history and today caches for tips & affirmations.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
    if (ok != true) return;

    await SettingsService.clearLocalData();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Local data cleared')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return PageScaffold(
      appBar: const AppTopBar(title: 'Settings'),
      bottomIndex: 6, // adjust if your bottom nav index differs for Settings
      body: AnimatedBackdrop(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 12),
          child: GlassCard(
            child: ListView(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 18),
              children: [
                const SectionHeroCard(
                  title: 'Settings',
                  subtitle: 'Personalize your experience',
                ),
                const SizedBox(height: 10),

                // ───────────────── Voice & Audio ─────────────────
                const _Section(title: 'Voice & Audio'),
                _SurfaceCard(
                  child: Column(
                    children: [
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Voice responses'),
                        subtitle: const Text(
                          'Read tips, affirmations, and chat replies aloud',
                        ),
                        value: _ttsEnabled,
                        onChanged: (v) async {
                          setState(() => _ttsEnabled = v);
                          await OpenAiTtsService.instance.setEnabled(v);
                          if (!v) await OpenAiTtsService.instance.stop();
                        },
                      ),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Mood-adaptive voice'),
                        subtitle: const Text(
                          'Voice tone adapts gently to your mood',
                        ),
                        value: _moodAdaptiveVoice,
                        onChanged: _ttsEnabled
                            ? (v) async {
                          setState(() => _moodAdaptiveVoice = v);
                          await OpenAiTtsService.instance
                              .setMoodAdaptive(v);
                        }
                            : null,
                      ),
                      const Divider(height: 18),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading:
                        const Icon(Icons.record_voice_over_outlined),
                        title: const Text('Voice settings'),
                        subtitle:
                        const Text('Speed, mood voice, test voice'),
                        trailing:
                        const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) =>
                              const VoiceSettingsScreen(),
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // ───────────────── Breathe ─────────────────
                const _Section(title: 'Breathe'),
                _SurfaceCard(
                  child: Column(
                    children: [
                      DropdownButtonFormField<BreathePreset>(
                        initialValue: _preset,
                        decoration:
                        const InputDecoration(labelText: 'Preset'),
                        items: BreathePreset.values
                            .map(
                              (p) => DropdownMenuItem(
                            value: p,
                            child: Text(p.label),
                          ),
                        )
                            .toList(),
                        onChanged: (v) async {
                          if (v == null) return;
                          setState(() => _preset = v);
                          await SettingsService.setPreset(v);
                        },
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<int>(
                        initialValue: _duration,
                        decoration: const InputDecoration(
                          labelText: 'Default duration',
                        ),
                        items: _durations
                            .map(
                              (s) => DropdownMenuItem(
                            value: s,
                            child: Text(
                              s >= 60 ? '${s ~/ 60} min' : '$s sec',
                            ),
                          ),
                        )
                            .toList(),
                        onChanged: (v) async {
                          if (v == null) return;
                          setState(() => _duration = v);
                          await SettingsService.setDurationSecs(v);
                        },
                      ),
                      const SizedBox(height: 12),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Haptics'),
                        value: _haptics,
                        onChanged: (v) async {
                          setState(() => _haptics = v);
                          await SettingsService.setHaptics(v);
                        },
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // ───────────────── Reminders ─────────────────
                const _Section(title: 'Reminders'),
                _SurfaceCard(
                  child: Column(
                    children: [
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: const Text('Daily recommendation reminder'),
                        subtitle:
                        Text('At ${_dailyReminderTime.format(context)}'),
                        value: _dailyReminderEnabled,
                        onChanged: (v) async {
                          setState(() => _dailyReminderEnabled = v);
                          await SettingsService.setDailyReminderEnabled(v);

                          if (!v) {
                            await NotificationService.instance
                                .cancelDailyResetNotification();
                            return;
                          }

                          final suggestion = await ProactiveSupportService.buildHomeSuggestion();
                          await NotificationService.instance.scheduleDailyRecommendationNotification(
                            uniqueKey: suggestion.id,
                            title: suggestion.notificationTitle,
                            body: suggestion.notificationBody,
                            routeName: suggestion.routeName,
                            routeArguments: suggestion.routeArguments,
                            hour: _dailyReminderTime.hour,
                            minute: _dailyReminderTime.minute,
                            openSettingsIfNeeded: true,
                          );
                        },
                      ),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        enabled: _dailyReminderEnabled,
                        title: const Text('Reminder time'),
                        subtitle: Text(_dailyReminderTime.format(context)),
                        trailing:
                        const Icon(Icons.chevron_right_rounded),
                        onTap: !_dailyReminderEnabled
                            ? null
                            : () async {
                          final picked = await showTimePicker(
                            context: context,
                            initialTime: _dailyReminderTime,
                          );
                          if (picked == null) return;

                          setState(() => _dailyReminderTime = picked);
                          await SettingsService.setDailyReminderTime(
                              picked);

                          final suggestion = await ProactiveSupportService.buildHomeSuggestion();
                          await NotificationService.instance.scheduleDailyRecommendationNotification(
                            uniqueKey: suggestion.id,
                            title: suggestion.notificationTitle,
                            body: suggestion.notificationBody,
                            routeName: suggestion.routeName,
                            routeArguments: suggestion.routeArguments,
                            hour: picked.hour,
                            minute: picked.minute,
                            openSettingsIfNeeded: false,
                          );
                        },
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 12),

                // ───────────────── Chat AI Persona ─────────────────
                const _Section(title: 'Chat AI Persona'),
                _SurfaceCard(
                  child: Column(
                    children: [
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.psychology_alt_rounded),
                        title: const Text('Coach / Therapist Tone'),
                        subtitle: const Text(
                          'Edit how MindCore AI speaks and supports users',
                        ),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (_) => const ChatPersonaScreen(),
                            ),
                          );
                        },
                      ),
                      const Divider(height: 18),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.auto_awesome_rounded),
                        title: const Text('Persona guidance'),
                        subtitle: const Text(
                          'Keep replies positive, validating, and actionable',
                        ),
                      ),
                    ],
                  ),
                ),


                const SizedBox(height: 12),

                // ───────────────── Trust & Safety ─────────────────
                const _Section(title: 'Trust & Safety'),
                _SurfaceCard(
                  child: Column(
                    children: [
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.health_and_safety_outlined),
                        title: const Text('Safety'),
                        subtitle: const Text('Support resources and safety guidance'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const SafetyScreen()),
                          );
                        },
                      ),
                      const Divider(height: 18),
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.lock_outline_rounded),
                        title: const Text('Privacy & Controls'),
                        subtitle: const Text('Local storage, export, and delete options'),
                        trailing: const Icon(Icons.chevron_right_rounded),
                        onTap: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const PrivacyControlsScreen()),
                          );
                        },
                      ),
                    ],
                  ),
                ),

                // ───────────────── Data ─────────────────
                const _Section(title: 'Data'),
                _SurfaceCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      FilledButton.tonal(
                        onPressed: _clearData,
                        child: const Text('Clear local data'),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Removes local journal/history and daily caches. '
                            'Does not affect any cloud data.',
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onSurface
                              .withValues(alpha: 0.65),
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 10),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// ───────────────── UI helpers ─────────────────

class _Section extends StatelessWidget {
  final String title;
  const _Section({required this.title});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
      child: Text(
        title,
        style: theme.textTheme.titleSmall?.copyWith(
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

/// Inner “surface” card used INSIDE the GlassCard, so your settings rows still
/// feel grouped and premium, but consistent with your global design.
class _SurfaceCard extends StatelessWidget {
  final Widget child;
  const _SurfaceCard({required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.dividerColor.withValues(alpha: 0.8),
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x14000000),
            blurRadius: 10,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: child,
    );
  }
}
