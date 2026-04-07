// lib/pages/settings_screen.dart
import 'package:flutter/material.dart';

import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/notification_service.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/premium_service.dart';
import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/services/subscription_service.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';
import 'package:mindcore_ai/models/tier_config.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

import 'package:mindcore_ai/pages/voice_settings_screen.dart';
import 'package:mindcore_ai/pages/chat_persona_screen.dart';
import 'package:mindcore_ai/pages/safety_screen.dart';
import 'package:mindcore_ai/pages/privacy_controls_screen.dart';
import 'package:mindcore_ai/pages/paywall_screen.dart';
import 'package:mindcore_ai/pages/disclaimer_screen.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  BreathePreset _preset    = BreathePreset.box;
  int           _duration  = 60;
  bool          _haptics   = true;
  final _durations = const [30, 60, 90, 180];

  bool      _dailyReminderEnabled = false;
  TimeOfDay _dailyReminderTime    = const TimeOfDay(hour: 8, minute: 0);

  bool _ttsEnabled        = true;
  bool _moodAdaptiveVoice = true;
  bool _loading           = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final preset       = await SettingsService.getPreset();
      final duration     = await SettingsService.getDurationSecs();
      final haptics      = await SettingsService.getHaptics();
      final dailyEnabled = await SettingsService.getDailyReminderEnabled();
      final dailyTime    = await SettingsService.getDailyReminderTime();
      final ttsEnabled   = await OpenAiTtsService.instance.getEnabled();
      final moodAdaptive = await OpenAiTtsService.instance.getMoodAdaptive();
      if (!mounted) return;
      setState(() {
        _preset               = preset;
        _duration             = duration;
        _haptics              = haptics;
        _dailyReminderEnabled = dailyEnabled;
        _dailyReminderTime    = dailyTime;
        _ttsEnabled           = ttsEnabled;
        _moodAdaptiveVoice    = moodAdaptive;
        _loading              = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Failed to load settings: $e')));
    }
  }

  Future<void> _clearData() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Clear local data?'),
        content: const Text(
            'Removes local journal, history and daily caches. Cloud data is unaffected.'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Clear')),
        ],
      ),
    );
    if (ok != true) return;
    await SettingsService.clearLocalData();
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Local data cleared')));
  }

  void _openPaywall() => Navigator.push(
      context, MaterialPageRoute(builder: (_) => const PaywallScreen()));

  void _openVoiceTopUp() => showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => const _VoiceTopUpSheet(),
      );

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Settings'),
      bottomIndex: 6,
      body: AnimatedBackdrop(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : ListView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                children: [

                  // ── Plan & Billing ─────────────────────────────────
                  _SectionLabel(label: 'Plan & Billing', icon: Icons.workspace_premium_rounded, color: AppColors.primary),
                  _PlanBillingCard(
                    onManagePlan: _openPaywall,
                    onBuyVoice:   _openVoiceTopUp,
                  ),
                  const SizedBox(height: 24),

                  // ── Voice & Audio ──────────────────────────────────
                  _SectionLabel(label: 'Voice & Audio', icon: Icons.graphic_eq_rounded, color: AppColors.mintDeep),
                  _SettingsCard(children: [
                    _ToggleRow(
                      icon: Icons.record_voice_over_rounded,
                      title: 'Voice responses',
                      subtitle: 'Read chat replies and tips aloud',
                      value: _ttsEnabled,
                      onChanged: (v) async {
                        setState(() => _ttsEnabled = v);
                        await OpenAiTtsService.instance.setEnabled(v);
                        if (!v) await OpenAiTtsService.instance.stop();
                      },
                    ),
                    _Divider(),
                    _ToggleRow(
                      icon: Icons.auto_awesome_rounded,
                      title: 'Mood-adaptive voice',
                      subtitle: 'Tone adapts gently to your mood',
                      value: _moodAdaptiveVoice,
                      enabled: _ttsEnabled,
                      onChanged: (v) async {
                        setState(() => _moodAdaptiveVoice = v);
                        await OpenAiTtsService.instance.setMoodAdaptive(v);
                      },
                    ),
                    _Divider(),
                    _NavRow(
                      icon: Icons.tune_rounded,
                      title: 'Voice settings',
                      subtitle: 'Speed, style and test voice',
                      onTap: () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const VoiceSettingsScreen())),
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── Breathing ──────────────────────────────────────
                  _SectionLabel(label: 'Breathing', icon: Icons.air_rounded, color: AppColors.violet),
                  _SettingsCard(children: [
                    _DropdownRow<BreathePreset>(
                      icon: Icons.self_improvement_rounded,
                      title: 'Preset',
                      value: _preset,
                      items: BreathePreset.values
                          .map((p) => DropdownMenuItem(value: p, child: Text(p.label)))
                          .toList(),
                      onChanged: (v) async {
                        if (v == null) return;
                        setState(() => _preset = v);
                        await SettingsService.setPreset(v);
                      },
                    ),
                    _Divider(),
                    _DropdownRow<int>(
                      icon: Icons.timer_outlined,
                      title: 'Default duration',
                      value: _duration,
                      items: _durations
                          .map((s) => DropdownMenuItem(
                              value: s,
                              child: Text(s >= 60 ? '${s ~/ 60} min' : '$s sec')))
                          .toList(),
                      onChanged: (v) async {
                        if (v == null) return;
                        setState(() => _duration = v);
                        await SettingsService.setDurationSecs(v);
                      },
                    ),
                    _Divider(),
                    _ToggleRow(
                      icon: Icons.vibration_rounded,
                      title: 'Haptics',
                      subtitle: 'Vibration feedback during exercises',
                      value: _haptics,
                      onChanged: (v) async {
                        setState(() => _haptics = v);
                        await SettingsService.setHaptics(v);
                      },
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── Reminders ──────────────────────────────────────
                  _SectionLabel(label: 'Reminders', icon: Icons.notifications_none_rounded, color: AppColors.amber),
                  _SettingsCard(children: [
                    _ToggleRow(
                      icon: Icons.alarm_rounded,
                      title: 'Daily reminder',
                      subtitle: 'At ${_dailyReminderTime.format(context)}',
                      value: _dailyReminderEnabled,
                      onChanged: (v) async {
                        setState(() => _dailyReminderEnabled = v);
                        await SettingsService.setDailyReminderEnabled(v);
                        if (!v) {
                          await NotificationService.instance.cancelDailyResetNotification();
                          return;
                        }
                        final s = await ProactiveSupportService.buildHomeSuggestion();
                        await NotificationService.instance
                            .scheduleDailyRecommendationNotification(
                          uniqueKey: s.id,
                          title: s.notificationTitle,
                          body: s.notificationBody,
                          routeName: s.routeName,
                          routeArguments: s.routeArguments,
                          hour: _dailyReminderTime.hour,
                          minute: _dailyReminderTime.minute,
                          openSettingsIfNeeded: true,
                        );
                      },
                    ),
                    _Divider(),
                    _NavRow(
                      icon: Icons.schedule_rounded,
                      title: 'Reminder time',
                      subtitle: _dailyReminderTime.format(context),
                      enabled: _dailyReminderEnabled,
                      onTap: !_dailyReminderEnabled
                          ? null
                          : () async {
                              final picked = await showTimePicker(
                                  context: context,
                                  initialTime: _dailyReminderTime);
                              if (picked == null) return;
                              setState(() => _dailyReminderTime = picked);
                              await SettingsService.setDailyReminderTime(picked);
                              final s = await ProactiveSupportService
                                  .buildHomeSuggestion();
                              await NotificationService.instance
                                  .scheduleDailyRecommendationNotification(
                                uniqueKey: s.id,
                                title: s.notificationTitle,
                                body: s.notificationBody,
                                routeName: s.routeName,
                                routeArguments: s.routeArguments,
                                hour: picked.hour,
                                minute: picked.minute,
                                openSettingsIfNeeded: false,
                              );
                            },
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── AI Persona ─────────────────────────────────────
                  _SectionLabel(label: 'AI Persona', icon: Icons.psychology_alt_rounded, color: AppColors.coral),
                  _SettingsCard(children: [
                    _NavRow(
                      icon: Icons.psychology_alt_rounded,
                      title: 'Conversation style',
                      subtitle: 'Choose how MindCore AI speaks to you',
                      onTap: () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const ChatPersonaScreen())),
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── Trust & Safety ─────────────────────────────────
                  _SectionLabel(label: 'Trust & Safety', icon: Icons.shield_outlined, color: AppColors.glowBlue),
                  _SettingsCard(children: [
                    _NavRow(
                      icon: Icons.health_and_safety_outlined,
                      title: 'Safety resources',
                      subtitle: 'Support lines and guidance',
                      onTap: () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const SafetyScreen())),
                    ),
                    _Divider(),
                    _NavRow(
                      icon: Icons.lock_outline_rounded,
                      title: 'Privacy & controls',
                      subtitle: 'Export, delete and storage options',
                      onTap: () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const PrivacyControlsScreen())),
                    ),
                    _Divider(),
                    _NavRow(
                      icon: Icons.info_outline_rounded,
                      title: 'Disclaimer',
                      subtitle: 'Not a substitute for professional help',
                      onTap: () => Navigator.push(context,
                          MaterialPageRoute(builder: (_) => const DisclaimerScreen())),
                    ),
                  ]),
                  const SizedBox(height: 24),

                  // ── Data ───────────────────────────────────────────
                  _SectionLabel(label: 'Data', icon: Icons.storage_rounded, color: AppColors.muted),
                  _SettingsCard(children: [
                    _ActionRow(
                      icon: Icons.delete_outline_rounded,
                      iconColor: const Color(0xFFA32D2D),
                      title: 'Clear local data',
                      subtitle: 'Remove local cache and history',
                      onTap: _clearData,
                    ),
                  ]),
                  const SizedBox(height: 16),
                ],
              ),
      ),
    );
  }
}

// ── Section label ─────────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  const _SectionLabel({required this.label, required this.icon, required this.color});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 14, color: color),
          const SizedBox(width: 6),
          Text(
            label.toUpperCase(),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: isDark
                  ? Colors.white.withValues(alpha: 0.45)
                  : Colors.black.withValues(alpha: 0.40),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Settings card ─────────────────────────────────────────────────────────────

class _SettingsCard extends StatelessWidget {
  final List<Widget> children;
  const _SettingsCard({required this.children});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.7)),
      ),
      child: Column(children: children),
    );
  }
}

// ── Row types ─────────────────────────────────────────────────────────────────

class _ToggleRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final bool value;
  final bool enabled;
  final ValueChanged<bool> onChanged;
  const _ToggleRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final dim    = !enabled;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Icon(icon,
              size: 18,
              color: dim
                  ? (isDark
                      ? Colors.white.withValues(alpha: 0.25)
                      : Colors.black.withValues(alpha: 0.20))
                  : AppColors.primary),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: tt.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: dim
                            ? (isDark
                                ? Colors.white.withValues(alpha: 0.30)
                                : Colors.black.withValues(alpha: 0.25))
                            : null)),
                Text(subtitle,
                    style: tt.bodySmall?.copyWith(
                        color: isDark
                            ? Colors.white.withValues(alpha: 0.40)
                            : Colors.black.withValues(alpha: 0.40))),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: enabled ? onChanged : null,
          ),
        ],
      ),
    );
  }
}

class _NavRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final bool enabled;
  const _NavRow({
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.enabled = true,
  });

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: [
            Icon(icon,
                size: 18,
                color: enabled
                    ? AppColors.primary
                    : (isDark
                        ? Colors.white.withValues(alpha: 0.25)
                        : Colors.black.withValues(alpha: 0.20))),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: tt.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: enabled
                              ? null
                              : (isDark
                                  ? Colors.white.withValues(alpha: 0.30)
                                  : Colors.black.withValues(alpha: 0.25)))),
                  Text(subtitle,
                      style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.40)
                              : Colors.black.withValues(alpha: 0.40))),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded,
                size: 20,
                color: isDark
                    ? Colors.white.withValues(alpha: 0.25)
                    : Colors.black.withValues(alpha: 0.25)),
          ],
        ),
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;
  const _ActionRow({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 13),
        child: Row(
          children: [
            Icon(icon, size: 18, color: iconColor),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: tt.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w600, color: iconColor)),
                  Text(subtitle,
                      style: tt.bodySmall?.copyWith(
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.40)
                              : Colors.black.withValues(alpha: 0.40))),
                ],
              ),
            ),
            Icon(Icons.chevron_right_rounded,
                size: 20,
                color: isDark
                    ? Colors.white.withValues(alpha: 0.25)
                    : Colors.black.withValues(alpha: 0.25)),
          ],
        ),
      ),
    );
  }
}

class _DropdownRow<T> extends StatelessWidget {
  final IconData icon;
  final String title;
  final T value;
  final List<DropdownMenuItem<T>> items;
  final ValueChanged<T?> onChanged;
  const _DropdownRow({
    required this.icon,
    required this.title,
    required this.value,
    required this.items,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Row(
        children: [
          Icon(icon, size: 18, color: AppColors.primary),
          const SizedBox(width: 14),
          Expanded(
            child: Text(title,
                style: tt.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
          ),
          DropdownButton<T>(
            value: value,
            items: items,
            onChanged: onChanged,
            underline: const SizedBox(),
            style: tt.bodyMedium,
            isDense: true,
          ),
        ],
      ),
    );
  }
}

class _Divider extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Divider(
        height: 0,
        thickness: 0.5,
        indent: 48,
        color: Theme.of(context).dividerColor.withValues(alpha: 0.5),
      );
}

// ── Plan & Billing card ───────────────────────────────────────────────────────

class _PlanBillingCard extends StatelessWidget {
  final VoidCallback onManagePlan;
  final VoidCallback onBuyVoice;
  const _PlanBillingCard({required this.onManagePlan, required this.onBuyVoice});

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return ValueListenableBuilder<TierConfig>(
      valueListenable: PremiumService.currentTier,
      builder: (context, tier, _) {
        return ValueListenableBuilder<UsageSnapshot>(
          valueListenable: UsageService.instance.snapshot,
          builder: (context, snap, _) {
            Color accent;
            if (tier.tier == AppTier.pro) {
              accent = AppColors.violet;
            } else if (tier.tier == AppTier.premium) {
              accent = AppColors.primary;
            } else {
              accent = const Color(0xFF64748B);
            }

            final msgFrac = tier.isUnlimited
                ? 0.0
                : (snap.messagesUsed / tier.monthlyMessages).clamp(0.0, 1.0);
            final voiceFrac = tier.monthlyVoiceSeconds <= 0
                ? 0.0
                : (snap.voiceSecondsUsed / tier.monthlyVoiceSeconds)
                    .clamp(0.0, 1.0);

            return GlassCard(
              glowColor: accent.withValues(alpha: 0.20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Plan badge row
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: accent.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                              color: accent.withValues(alpha: 0.35)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.workspace_premium_rounded,
                                size: 13, color: accent),
                            const SizedBox(width: 5),
                            Text(tier.displayName.toUpperCase(),
                                style: tt.labelSmall?.copyWith(
                                    color: accent,
                                    fontWeight: FontWeight.w800,
                                    fontSize: 11)),
                          ],
                        ),
                      ),
                      const Spacer(),
                      if (tier.tier != AppTier.trial)
                        Text(
                          '\u20ac${tier.monthlyPrice.toStringAsFixed(2)}/mo',
                          style: tt.bodySmall?.copyWith(
                              color: isDark
                                  ? Colors.white.withValues(alpha: 0.50)
                                  : Colors.black.withValues(alpha: 0.45),
                              fontWeight: FontWeight.w600),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Messages
                  _UsageLabel(
                    icon: Icons.chat_rounded,
                    label: 'Messages',
                    detail: tier.isUnlimited
                        ? 'Unlimited'
                        : '${snap.messagesUsed} / ${tier.monthlyMessages} used',
                    color: accent,
                    isDark: isDark,
                    tt: tt,
                  ),
                  const SizedBox(height: 6),
                  _UsageBar(fraction: msgFrac, color: accent, warn: msgFrac > 0.80),
                  const SizedBox(height: 14),

                  // Voice
                  _UsageLabel(
                    icon: Icons.mic_rounded,
                    label: 'Voice minutes',
                    detail:
                        '${(snap.voiceSecondsUsed / 60).floor()} / ${tier.voiceMinutes} min used',
                    color: AppColors.mintDeep,
                    isDark: isDark,
                    tt: tt,
                  ),
                  const SizedBox(height: 6),
                  _UsageBar(
                      fraction: voiceFrac,
                      color: AppColors.mintDeep,
                      warn: voiceFrac > 0.80),
                  const SizedBox(height: 16),

                  // Buttons
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: onManagePlan,
                          icon: const Icon(
                              Icons.workspace_premium_rounded, size: 16),
                          label: Text(
                            tier.tier == AppTier.trial
                                ? 'Upgrade'
                                : 'Change plan',
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          style: FilledButton.styleFrom(
                              backgroundColor: accent,
                              minimumSize: const Size.fromHeight(44),
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10))),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: onBuyVoice,
                          icon: Icon(Icons.mic_rounded,
                              size: 16, color: AppColors.mintDeep),
                          label: Text('Voice mins',
                              style: TextStyle(
                                  fontWeight: FontWeight.w800,
                                  color: AppColors.mintDeep)),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(44),
                            side: BorderSide(
                                color:
                                    AppColors.mintDeep.withValues(alpha: 0.50)),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _UsageLabel extends StatelessWidget {
  final IconData icon;
  final String label;
  final String detail;
  final Color color;
  final bool isDark;
  final TextTheme tt;
  const _UsageLabel({
    required this.icon,
    required this.label,
    required this.detail,
    required this.color,
    required this.isDark,
    required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Row(children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 6),
          Text(label,
              style: tt.labelSmall?.copyWith(fontWeight: FontWeight.w700)),
        ]),
        Text(detail,
            style: tt.labelSmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.45)
                    : Colors.black.withValues(alpha: 0.45))),
      ],
    );
  }
}

// ── Usage bar ─────────────────────────────────────────────────────────────────

class _UsageBar extends StatelessWidget {
  final double fraction;
  final Color color;
  final bool warn;
  const _UsageBar(
      {required this.fraction, required this.color, this.warn = false});

  @override
  Widget build(BuildContext context) {
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    final barColor = warn ? const Color(0xFFE24B4A) : color;
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: SizedBox(
        height: 5,
        child: LinearProgressIndicator(
          value: fraction,
          backgroundColor: isDark
              ? Colors.white.withValues(alpha: 0.10)
              : Colors.black.withValues(alpha: 0.07),
          valueColor: AlwaysStoppedAnimation<Color>(barColor),
          minHeight: 5,
        ),
      ),
    );
  }
}

// ── Voice top-up sheet ────────────────────────────────────────────────────────

class _VoiceTopUpSheet extends StatefulWidget {
  const _VoiceTopUpSheet();
  @override
  State<_VoiceTopUpSheet> createState() => _VoiceTopUpSheetState();
}

class _VoiceTopUpSheetState extends State<_VoiceTopUpSheet> {
  final _sub = SubscriptionService();
  bool _loading = false;

  @override
  void initState() {
    super.initState();
    _sub.init().catchError((e) => debugPrint('VoiceTopUpSheet: $e'));
  }

  @override
  void dispose() {
    _sub.dispose();
    super.dispose();
  }

  Future<void> _buy(String productId) async {
    final product = _sub.voicePackProduct(productId);
    if (product == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Store not available. Try again.')));
      }
      return;
    }
    setState(() => _loading = true);
    try {
      await _sub.buy(product);
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      debugPrint('VoiceTopUpSheet: buy failed — $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final cs     = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      decoration: BoxDecoration(
        color: cs.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
      ),
      padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom + 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 12, bottom: 8),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.20)
                    : Colors.black.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 4),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: AppColors.mintDeep.withValues(alpha: 0.12),
                    border: Border.all(
                        color: AppColors.mintDeep.withValues(alpha: 0.30)),
                  ),
                  child: Icon(Icons.mic_rounded,
                      color: AppColors.mintDeep, size: 20),
                ),
                const SizedBox(width: 12),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Voice Top-Ups',
                        style: tt.titleMedium?.copyWith(
                            fontWeight: FontWeight.w900,
                            color: AppColors.mintDeep)),
                    Text('Added instantly to your account',
                        style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.50)
                                : const Color(0xFF475467))),
                  ],
                ),
                const Spacer(),
                IconButton(
                  icon: Icon(Icons.close,
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.50)
                          : Colors.black.withValues(alpha: 0.40)),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20),
            child: Divider(height: 16,
                color: isDark
                    ? Colors.white.withValues(alpha: 0.10)
                    : Colors.black.withValues(alpha: 0.08)),
          ),
          ...VoicePackConfig.all.map((pack) => Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                child: Row(
                  children: [
                    Container(
                      width: 52,
                      height: 52,
                      decoration: BoxDecoration(
                        color: AppColors.mintDeep.withValues(alpha: 0.10),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                            color: AppColors.mintDeep.withValues(alpha: 0.25)),
                      ),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text('${pack.minutes}',
                              style: tt.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w900,
                                  color: AppColors.mintDeep,
                                  height: 1.0)),
                          Text('min',
                              style: TextStyle(
                                  fontSize: 10,
                                  color: AppColors.mintDeep
                                      .withValues(alpha: 0.80),
                                  fontWeight: FontWeight.w600)),
                        ],
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(pack.displayName,
                              style: tt.titleSmall
                                  ?.copyWith(fontWeight: FontWeight.w800)),
                          Text(pack.tagline,
                              style: tt.bodySmall?.copyWith(
                                  color: isDark
                                      ? Colors.white.withValues(alpha: 0.50)
                                      : const Color(0xFF475467))),
                        ],
                      ),
                    ),
                    const SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(pack.priceLabel,
                            style: tt.titleMedium?.copyWith(
                                fontWeight: FontWeight.w900,
                                color: AppColors.mintDeep)),
                        const SizedBox(height: 4),
                        SizedBox(
                          width: 76,
                          height: 36,
                          child: FilledButton(
                            onPressed:
                                _loading ? null : () => _buy(pack.productId),
                            style: FilledButton.styleFrom(
                              backgroundColor: AppColors.mintDeep,
                              padding:
                                  const EdgeInsets.symmetric(horizontal: 12),
                              minimumSize: Size.zero,
                              tapTargetSize:
                                  MaterialTapTargetSize.shrinkWrap,
                              shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(8)),
                            ),
                            child: _loading
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: Colors.white))
                                : Text('Buy',
                                    style: tt.labelSmall?.copyWith(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w800)),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              )),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
            child: Text(
              'Minutes stack on top of your plan and reset monthly.',
              style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.35)
                      : Colors.black.withValues(alpha: 0.35)),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}
