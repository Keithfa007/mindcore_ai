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
import 'package:mindcore_ai/widgets/section_hero_card.dart';

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
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Failed to load settings: $e')));
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

  void _openPaywall() {
    Navigator.push(context,
        MaterialPageRoute(builder: (_) => const PaywallScreen()));
  }

  // Opens a voice-only bottom sheet — does NOT show subscription plans
  void _openVoiceTopUp() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _VoiceTopUpSheet(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme  = Theme.of(context);

    return PageScaffold(
      appBar: const AppTopBar(title: 'Settings'),
      bottomIndex: 6,
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
                          subtitle: 'Personalise your experience'),
                      const SizedBox(height: 10),

                      // ─────────── Plan & Billing ─────────────────────
                      const _Section(title: 'Plan & Billing'),
                      _PlanBillingCard(
                        onManagePlan: _openPaywall,
                        onBuyVoice:   _openVoiceTopUp,   // ← separate handler
                      ),
                      const SizedBox(height: 12),

                      // ─────────── Voice & Audio ──────────────────────
                      const _Section(title: 'Voice & Audio'),
                      _SurfaceCard(
                        child: Column(
                          children: [
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title: const Text('Voice responses'),
                              subtitle: const Text(
                                  'Read tips, affirmations, and chat replies aloud'),
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
                                  'Voice tone adapts gently to your mood'),
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
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) =>
                                          const VoiceSettingsScreen())),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),

                      // ─────────── Breathe ────────────────────────────
                      const _Section(title: 'Breathe'),
                      _SurfaceCard(
                        child: Column(
                          children: [
                            DropdownButtonFormField<BreathePreset>(
                              initialValue: _preset,
                              decoration:
                                  const InputDecoration(labelText: 'Preset'),
                              items: BreathePreset.values
                                  .map((p) => DropdownMenuItem(
                                      value: p, child: Text(p.label)))
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
                                  labelText: 'Default duration'),
                              items: _durations
                                  .map((s) => DropdownMenuItem(
                                      value: s,
                                      child: Text(s >= 60
                                          ? '${s ~/ 60} min'
                                          : '$s sec')))
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

                      // ─────────── Reminders ──────────────────────────
                      const _Section(title: 'Reminders'),
                      _SurfaceCard(
                        child: Column(
                          children: [
                            SwitchListTile(
                              contentPadding: EdgeInsets.zero,
                              title:
                                  const Text('Daily recommendation reminder'),
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
                                final suggestion = await ProactiveSupportService
                                    .buildHomeSuggestion();
                                await NotificationService.instance
                                    .scheduleDailyRecommendationNotification(
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
                              subtitle:
                                  Text(_dailyReminderTime.format(context)),
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: !_dailyReminderEnabled
                                  ? null
                                  : () async {
                                      final picked = await showTimePicker(
                                        context: context,
                                        initialTime: _dailyReminderTime,
                                      );
                                      if (picked == null) return;
                                      setState(
                                          () => _dailyReminderTime = picked);
                                      await SettingsService
                                          .setDailyReminderTime(picked);
                                      final suggestion =
                                          await ProactiveSupportService
                                              .buildHomeSuggestion();
                                      await NotificationService.instance
                                          .scheduleDailyRecommendationNotification(
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

                      // ─────────── Chat AI Persona ────────────────────
                      const _Section(title: 'Chat AI Persona'),
                      _SurfaceCard(
                        child: ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.psychology_alt_rounded),
                          title: const Text('Coach / Therapist Tone'),
                          subtitle: const Text(
                              'Edit how MindCore AI speaks and supports you'),
                          trailing: const Icon(Icons.chevron_right_rounded),
                          onTap: () => Navigator.push(
                              context,
                              MaterialPageRoute(
                                  builder: (_) => const ChatPersonaScreen())),
                        ),
                      ),
                      const SizedBox(height: 12),

                      // ─────────── Trust & Safety ─────────────────────
                      const _Section(title: 'Trust & Safety'),
                      _SurfaceCard(
                        child: Column(
                          children: [
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading:
                                  const Icon(Icons.health_and_safety_outlined),
                              title: const Text('Safety'),
                              subtitle: const Text(
                                  'Support resources and safety guidance'),
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) => const SafetyScreen())),
                            ),
                            const Divider(height: 18),
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(Icons.lock_outline_rounded),
                              title: const Text('Privacy & Controls'),
                              subtitle: const Text(
                                  'Local storage, export, and delete options'),
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) =>
                                          const PrivacyControlsScreen())),
                            ),
                            const Divider(height: 18),
                            ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(Icons.info_outline_rounded),
                              title: const Text('Disclaimer'),
                              subtitle: const Text(
                                  'Not a substitute for professional help'),
                              trailing: const Icon(Icons.chevron_right_rounded),
                              onTap: () => Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                      builder: (_) =>
                                          const DisclaimerScreen())),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),

                      // ─────────── Data ───────────────────────────────
                      const _Section(title: 'Data'),
                      _SurfaceCard(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            FilledButton.tonal(
                                onPressed: _clearData,
                                child: const Text('Clear local data')),
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

// ── Plan & Billing card ───────────────────────────────────────────────────────

class _PlanBillingCard extends StatelessWidget {
  final VoidCallback onManagePlan;
  final VoidCallback onBuyVoice;        // ← separate callback for voice top-up
  const _PlanBillingCard({
    required this.onManagePlan,
    required this.onBuyVoice,
  });

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

            final msgUsed  = snap.messagesUsed;
            final msgTotal = tier.monthlyMessages;
            final msgFrac  = tier.isUnlimited
                ? 0.0
                : (msgUsed / msgTotal).clamp(0.0, 1.0);

            final voiceUsed    = snap.voiceSecondsUsed;
            final voiceTotal   = tier.monthlyVoiceSeconds;
            final voiceFrac    = voiceTotal <= 0
                ? 0.0
                : (voiceUsed / voiceTotal).clamp(0.0, 1.0);
            final voiceMinUsed  = (voiceUsed / 60).floor();
            final voiceMinTotal = tier.voiceMinutes;

            return _SurfaceCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Plan badge
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 4),
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

                  // Message usage
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(children: [
                        Icon(Icons.chat_rounded, size: 13, color: accent),
                        const SizedBox(width: 6),
                        Text('Messages',
                            style: tt.labelSmall
                                ?.copyWith(fontWeight: FontWeight.w700)),
                      ]),
                      Text(
                        tier.isUnlimited
                            ? 'Unlimited'
                            : '$msgUsed / $msgTotal used',
                        style: tt.labelSmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.50)
                                : Colors.black.withValues(alpha: 0.45)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  _UsageBar(
                      fraction: msgFrac, color: accent, warn: msgFrac > 0.80),
                  const SizedBox(height: 14),

                  // Voice usage
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(children: [
                        Icon(Icons.mic_rounded,
                            size: 13, color: AppColors.mintDeep),
                        const SizedBox(width: 6),
                        Text('Voice minutes',
                            style: tt.labelSmall
                                ?.copyWith(fontWeight: FontWeight.w700)),
                      ]),
                      Text(
                        '$voiceMinUsed / $voiceMinTotal min used',
                        style: tt.labelSmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.50)
                                : Colors.black.withValues(alpha: 0.45)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  _UsageBar(
                      fraction: voiceFrac,
                      color: AppColors.mintDeep,
                      warn: voiceFrac > 0.80),
                  const SizedBox(height: 16),

                  // Action buttons
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: onManagePlan,
                          icon: const Icon(Icons.workspace_premium_rounded,
                              size: 16),
                          label: Text(
                              tier.tier == AppTier.trial
                                  ? 'Upgrade plan'
                                  : 'Change plan',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800)),
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
                          onPressed: onBuyVoice,   // ← now opens voice-only sheet
                          icon: Icon(Icons.mic_rounded,
                              size: 16, color: AppColors.mintDeep),
                          label: Text('Buy voice mins',
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

// ── Voice top-up bottom sheet ─────────────────────────────────────────────────
// Shows ONLY the three voice packs — no subscription plans

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
    _sub.init().catchError((e) {
      debugPrint('VoiceTopUpSheet: IAP init failed — $e');
    });
  }

  @override
  void dispose() {
    _sub.dispose();
    super.dispose();
  }

  Future<void> _buy(productId) async {
    final product = _sub.voicePackProduct(productId as String);
    if (product == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Store not available right now. Please try again.'),
        ));
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
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Handle bar
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

          // Header
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
                    Text('Voice Minute Top-Ups',
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

          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20),
            child: Divider(),
          ),

          // Pack rows
          ...VoicePackConfig.all.map((pack) => _PackRow(
                pack: pack,
                loading: _loading,
                onBuy: () => _buy(pack.productId),
                isDark: isDark,
                tt: tt,
              )),

          // Footer note
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
            child: Text(
              'Minutes stack on top of your plan allowance and reset monthly.',
              style: tt.bodySmall?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.35)
                      : Colors.black.withValues(alpha: 0.40)),
              textAlign: TextAlign.center,
            ),
          ),
        ],
      ),
    );
  }
}

class _PackRow extends StatelessWidget {
  final VoicePackConfig pack;
  final bool loading;
  final VoidCallback onBuy;
  final bool isDark;
  final TextTheme tt;
  const _PackRow({
    required this.pack,
    required this.loading,
    required this.onBuy,
    required this.isDark,
    required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      child: Row(
        children: [
          // Minutes badge
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
                        color: AppColors.mintDeep.withValues(alpha: 0.80),
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Labels
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
          // Price + button
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
                  onPressed: loading ? null : onBuy,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.mintDeep,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(8)),
                  ),
                  child: loading
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(
                              strokeWidth: 2, color: Colors.white))
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
        height: 6,
        child: LinearProgressIndicator(
          value: fraction,
          backgroundColor: isDark
              ? Colors.white.withValues(alpha: 0.10)
              : Colors.black.withValues(alpha: 0.08),
          valueColor: AlwaysStoppedAnimation<Color>(barColor),
          minHeight: 6,
        ),
      ),
    );
  }
}

// ── Section header ────────────────────────────────────────────────────────────

class _Section extends StatelessWidget {
  final String title;
  const _Section({required this.title});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(4, 8, 4, 6),
      child: Text(title,
          style: Theme.of(context)
              .textTheme
              .titleSmall
              ?.copyWith(fontWeight: FontWeight.w800)),
    );
  }
}

// ── Inner surface card ────────────────────────────────────────────────────────

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
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.8)),
        boxShadow: const [
          BoxShadow(
              color: Color(0x14000000), blurRadius: 10, offset: Offset(0, 2))
        ],
      ),
      child: child,
    );
  }
}
