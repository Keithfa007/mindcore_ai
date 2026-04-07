// lib/pages/safety_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:mindcore_ai/widgets/page_scaffold.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';

class SafetyScreen extends StatelessWidget {
  const SafetyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final tt     = Theme.of(context).textTheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return PageScaffold(
      appBar: const AppTopBar(title: 'Safety & Support'),
      body: AnimatedBackdrop(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
          children: [

            // ── Emergency banner ────────────────────────────────────────────
            _EmergencyBanner(tt: tt, isDark: isDark),
            const SizedBox(height: 20),

            // ── Not alone card ───────────────────────────────────────────────
            _InfoSection(
              icon: Icons.favorite_rounded,
              iconColor: const Color(0xFFE24B4A),
              title: 'You are not alone',
              isDark: isDark,
              tt: tt,
              child: Text(
                'Whatever you are feeling right now — MindCore AI hears you. '
                'This page exists because your safety matters more than anything else. '
                'Please reach out to a real person if you are struggling.',
                style: tt.bodyMedium?.copyWith(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.75)
                      : const Color(0xFF344054),
                  height: 1.6,
                ),
              ),
            ),
            const SizedBox(height: 16),

            // ── What MindCore AI is not ──────────────────────────────────────
            _InfoSection(
              icon: Icons.info_outline_rounded,
              iconColor: AppColors.primary,
              title: 'Important — what MindCore AI is not',
              isDark: isDark,
              tt: tt,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _BulletPoint(
                    text: 'MindCore AI is not a crisis service or emergency helpline.',
                    isDark: isDark, tt: tt,
                  ),
                  _BulletPoint(
                    text: 'It cannot contact emergency services on your behalf.',
                    isDark: isDark, tt: tt,
                  ),
                  _BulletPoint(
                    text: 'It is not a replacement for a licensed therapist or doctor.',
                    isDark: isDark, tt: tt,
                  ),
                  _BulletPoint(
                    text: 'In any emergency, always call your local emergency number first.',
                    isDark: isDark, tt: tt,
                    bold: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // ── Crisis helplines ─────────────────────────────────────────────
            _SectionLabel(label: 'Crisis helplines', icon: Icons.phone_rounded,
                color: const Color(0xFFE24B4A), isDark: isDark, tt: tt),
            const SizedBox(height: 8),

            _HelplineRegion(
              region: 'Malta',
              flag: '🇲🇹',
              lines: const [
                _Helpline('Emergency services', '112', '112'),
                _Helpline('Mental health helpline', '1579', '1579'),
                _Helpline('Supportline (24/7)', '179', '179'),
              ],
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),

            _HelplineRegion(
              region: 'Europe',
              flag: '🇪🇺',
              lines: const [
                _Helpline('Emergency services', '112', '112'),
                _Helpline('European crisis line (findahelpline.com)', 'findahelpline.com', null),
              ],
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),

            _HelplineRegion(
              region: 'United Kingdom',
              flag: '🇬🇧',
              lines: const [
                _Helpline('Emergency services', '999', '999'),
                _Helpline('Samaritans (24/7)', '116 123', '116123'),
                _Helpline('Crisis text line', 'Text SHOUT to 85258', null),
              ],
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),

            _HelplineRegion(
              region: 'USA & Canada',
              flag: '🇺🇸',
              lines: const [
                _Helpline('Emergency services', '911', '911'),
                _Helpline('988 Suicide & Crisis Lifeline', '988', '988'),
                _Helpline('Crisis text line', 'Text HOME to 741741', null),
              ],
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 10),

            _HelplineRegion(
              region: 'Australia',
              flag: '🇦🇺',
              lines: const [
                _Helpline('Emergency services', '000', '000'),
                _Helpline('Lifeline (24/7)', '13 11 14', '131114'),
                _Helpline('Beyond Blue', '1300 22 4636', '1300224636'),
              ],
              isDark: isDark, tt: tt,
            ),
            const SizedBox(height: 20),

            // ── Warning signs ────────────────────────────────────────────────
            _SectionLabel(label: 'Warning signs to watch for', icon: Icons.warning_amber_rounded,
                color: const Color(0xFFBA7517), isDark: isDark, tt: tt),
            const SizedBox(height: 8),
            _InfoSection(
              icon: Icons.warning_amber_rounded,
              iconColor: const Color(0xFFBA7517),
              title: 'Seek help if you or someone you know is experiencing…',
              isDark: isDark,
              tt: tt,
              child: Column(
                children: [
                  _WarnRow(text: 'Thoughts of suicide or self-harm', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Feeling hopeless or trapped with no way out', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Withdrawing from family, friends and activities', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Extreme mood swings, rage or reckless behaviour', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Talking about being a burden to others', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Giving away prized possessions', isDark: isDark, tt: tt),
                  _WarnRow(text: 'Increased use of alcohol or drugs', isDark: isDark, tt: tt),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── In-app coping tools ──────────────────────────────────────────
            _SectionLabel(label: 'Tools available right now', icon: Icons.self_improvement_rounded,
                color: AppColors.mintDeep, isDark: isDark, tt: tt),
            const SizedBox(height: 8),
            _ToolsCard(isDark: isDark, tt: tt, context: context),
            const SizedBox(height: 20),

            // ── Quick reset CTA ──────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: isDark ? 0.12 : 0.07),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                    color: AppColors.primary.withValues(alpha: 0.30)),
              ),
              child: Column(
                children: [
                  Icon(Icons.air_rounded, color: AppColors.primary, size: 32),
                  const SizedBox(height: 10),
                  Text('Take a moment right now',
                      textAlign: TextAlign.center,
                      style: tt.titleMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                          color: AppColors.primary)),
                  const SizedBox(height: 6),
                  Text(
                    'A quick breathing reset can help ground you when '
                    'things feel overwhelming.',
                    textAlign: TextAlign.center,
                    style: tt.bodySmall?.copyWith(
                      color: isDark
                          ? Colors.white.withValues(alpha: 0.60)
                          : const Color(0xFF475467),
                      height: 1.5,
                    ),
                  ),
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: () =>
                          Navigator.of(context).pushNamed('/reset'),
                      icon: const Icon(Icons.air_rounded, size: 18),
                      label: const Text('Start quick reset',
                          style: TextStyle(fontWeight: FontWeight.w800)),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppColors.primary,
                        minimumSize: const Size.fromHeight(48),
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Footer
            Text(
              'If you are in immediate danger, do not use this app — '
              'call emergency services immediately.',
              textAlign: TextAlign.center,
              style: tt.bodySmall?.copyWith(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.35)
                    : Colors.black.withValues(alpha: 0.35),
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Emergency banner ────────────────────────────────────────────────────────

class _EmergencyBanner extends StatelessWidget {
  final TextTheme tt;
  final bool isDark;
  const _EmergencyBanner({required this.tt, required this.isDark});

  Future<void> _call(String number) async {
    final uri = Uri.parse('tel:$number');
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFA32D2D).withValues(alpha: isDark ? 0.20 : 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
            color: const Color(0xFFA32D2D).withValues(alpha: 0.45), width: 1.5),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFA32D2D).withValues(alpha: 0.15),
                ),
                child: const Icon(Icons.emergency_rounded,
                    color: Color(0xFFE24B4A), size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('In immediate danger?',
                        style: tt.titleSmall?.copyWith(
                            fontWeight: FontWeight.w900,
                            color: const Color(0xFFE24B4A))),
                    Text('Call your local emergency number now.',
                        style: tt.bodySmall?.copyWith(
                            color: isDark
                                ? Colors.white.withValues(alpha: 0.70)
                                : const Color(0xFF344054))),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _CallButton(
                  label: 'Malta / EU',
                  number: '112',
                  onTap: () => _call('112'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _CallButton(
                  label: 'UK',
                  number: '999',
                  onTap: () => _call('999'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: _CallButton(
                  label: 'USA / CA',
                  number: '911',
                  onTap: () => _call('911'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CallButton extends StatelessWidget {
  final String label;
  final String number;
  final VoidCallback onTap;
  const _CallButton(
      {required this.label, required this.number, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: const Color(0xFFA32D2D).withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(10),
          border:
              Border.all(color: const Color(0xFFE24B4A).withValues(alpha: 0.40)),
        ),
        child: Column(
          children: [
            const Icon(Icons.phone_rounded,
                color: Color(0xFFE24B4A), size: 16),
            const SizedBox(height: 3),
            Text(number,
                style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w900,
                    color: Color(0xFFE24B4A))),
            Text(label,
                style: TextStyle(
                    fontSize: 10,
                    color: const Color(0xFFE24B4A).withValues(alpha: 0.75))),
          ],
        ),
      ),
    );
  }
}

// ── Section label ────────────────────────────────────────────────────────────

class _SectionLabel extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final bool isDark;
  final TextTheme tt;
  const _SectionLabel(
      {required this.label,
      required this.icon,
      required this.color,
      required this.isDark,
      required this.tt});

  @override
  Widget build(BuildContext context) {
    return Row(
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
    );
  }
}

// ── Info section card ────────────────────────────────────────────────────────

class _InfoSection extends StatelessWidget {
  final IconData icon;
  final Color iconColor;
  final String title;
  final Widget child;
  final bool isDark;
  final TextTheme tt;
  const _InfoSection({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.child,
    required this.isDark,
    required this.tt,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: iconColor.withValues(alpha: 0.12),
                ),
                child: Icon(icon, color: iconColor, size: 17),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(title,
                    style: tt.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

// ── Helpline region card ─────────────────────────────────────────────────────

class _Helpline {
  final String name;
  final String display;
  final String? dialNumber;
  const _Helpline(this.name, this.display, this.dialNumber);
}

class _HelplineRegion extends StatelessWidget {
  final String region;
  final String flag;
  final List<_Helpline> lines;
  final bool isDark;
  final TextTheme tt;
  const _HelplineRegion({
    required this.region,
    required this.flag,
    required this.lines,
    required this.isDark,
    required this.tt,
  });

  Future<void> _call(String number) async {
    final uri = Uri.parse('tel:$number');
    if (await canLaunchUrl(uri)) await launchUrl(uri);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.7)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Region header
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
            child: Row(
              children: [
                Text(flag, style: const TextStyle(fontSize: 18)),
                const SizedBox(width: 8),
                Text(region,
                    style: tt.titleSmall
                        ?.copyWith(fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          const Divider(height: 0, thickness: 0.5, indent: 14),
          // Lines
          ...lines.asMap().entries.map((e) {
            final line  = e.value;
            final isLast = e.key == lines.length - 1;
            return Column(
              children: [
                InkWell(
                  onTap: line.dialNumber != null
                      ? () => _call(line.dialNumber!)
                      : null,
                  borderRadius: isLast
                      ? const BorderRadius.vertical(
                          bottom: Radius.circular(14))
                      : BorderRadius.zero,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 11),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(line.name,
                                  style: tt.bodySmall?.copyWith(
                                      color: isDark
                                          ? Colors.white
                                              .withValues(alpha: 0.75)
                                          : const Color(0xFF344054))),
                              Text(line.display,
                                  style: tt.bodyMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                      color: const Color(0xFFE24B4A))),
                            ],
                          ),
                        ),
                        if (line.dialNumber != null)
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 10, vertical: 5),
                            decoration: BoxDecoration(
                              color: const Color(0xFFE24B4A)
                                  .withValues(alpha: 0.10),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                  color: const Color(0xFFE24B4A)
                                      .withValues(alpha: 0.30)),
                            ),
                            child: const Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(Icons.phone_rounded,
                                    size: 13,
                                    color: Color(0xFFE24B4A)),
                                SizedBox(width: 4),
                                Text('Call',
                                    style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700,
                                        color: Color(0xFFE24B4A))),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                if (!isLast)
                  const Divider(height: 0, thickness: 0.5, indent: 14),
              ],
            );
          }),
        ],
      ),
    );
  }
}

// ── In-app tools card ────────────────────────────────────────────────────────

class _ToolsCard extends StatelessWidget {
  final bool isDark;
  final TextTheme tt;
  final BuildContext context;
  const _ToolsCard(
      {required this.isDark, required this.tt, required this.context});

  @override
  Widget build(BuildContext outerContext) {
    final theme = Theme.of(outerContext);
    final tools = [
      _Tool(Icons.air_rounded, 'Breathe', 'Guided breathing to calm your nervous system', '/breathe', AppColors.primary),
      _Tool(Icons.self_improvement_rounded, 'SOS grounding', '5-4-3-2-1 grounding technique for crisis moments', '/sos', const Color(0xFFE24B4A)),
      _Tool(Icons.headphones_rounded, 'Relax audio', 'Calming sounds to help you feel safe', '/relax-audio', AppColors.mintDeep),
      _Tool(Icons.chat_rounded, 'Talk to MindCore AI', 'Share what\'s on your mind right now', '/chat', AppColors.violet),
    ];

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: theme.dividerColor.withValues(alpha: 0.7)),
      ),
      child: Column(
        children: tools.asMap().entries.map((e) {
          final tool   = e.value;
          final isLast = e.key == tools.length - 1;
          return Column(
            children: [
              InkWell(
                onTap: () => Navigator.of(outerContext).pushNamed(tool.route),
                borderRadius: isLast
                    ? const BorderRadius.vertical(bottom: Radius.circular(16))
                    : BorderRadius.zero,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 16, vertical: 12),
                  child: Row(
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: tool.color.withValues(alpha: 0.12),
                          border: Border.all(
                              color: tool.color.withValues(alpha: 0.25)),
                        ),
                        child:
                            Icon(tool.icon, color: tool.color, size: 18),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(tool.name,
                                style: tt.bodyMedium?.copyWith(
                                    fontWeight: FontWeight.w700)),
                            Text(tool.subtitle,
                                style: tt.bodySmall?.copyWith(
                                    color: isDark
                                        ? Colors.white
                                            .withValues(alpha: 0.45)
                                        : const Color(0xFF64748B))),
                          ],
                        ),
                      ),
                      Icon(Icons.chevron_right_rounded,
                          size: 18,
                          color: isDark
                              ? Colors.white.withValues(alpha: 0.25)
                              : Colors.black.withValues(alpha: 0.25)),
                    ],
                  ),
                ),
              ),
              if (!isLast)
                const Divider(height: 0, thickness: 0.5, indent: 66),
            ],
          );
        }).toList(),
      ),
    );
  }
}

class _Tool {
  final IconData icon;
  final String name;
  final String subtitle;
  final String route;
  final Color color;
  const _Tool(this.icon, this.name, this.subtitle, this.route, this.color);
}

// ── Bullet + Warning rows ────────────────────────────────────────────────────

class _BulletPoint extends StatelessWidget {
  final String text;
  final bool bold;
  final bool isDark;
  final TextTheme tt;
  const _BulletPoint(
      {required this.text,
      required this.isDark,
      required this.tt,
      this.bold = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.primary.withValues(alpha: 0.60),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text,
                style: tt.bodyMedium?.copyWith(
                    fontWeight:
                        bold ? FontWeight.w700 : FontWeight.normal,
                    color: isDark
                        ? Colors.white.withValues(alpha: bold ? 0.90 : 0.72)
                        : (bold
                            ? const Color(0xFF0E1320)
                            : const Color(0xFF344054)),
                    height: 1.5)),
          ),
        ],
      ),
    );
  }
}

class _WarnRow extends StatelessWidget {
  final String text;
  final bool isDark;
  final TextTheme tt;
  const _WarnRow(
      {required this.text, required this.isDark, required this.tt});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: const Icon(Icons.warning_amber_rounded,
                size: 14, color: Color(0xFFBA7517)),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(text,
                style: tt.bodyMedium?.copyWith(
                    color: isDark
                        ? Colors.white.withValues(alpha: 0.75)
                        : const Color(0xFF344054),
                    height: 1.5)),
          ),
        ],
      ),
    );
  }
}
