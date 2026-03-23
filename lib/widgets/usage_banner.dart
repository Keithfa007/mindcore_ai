// lib/widgets/usage_banner.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/models/tier_config.dart';

class UsageBanner extends StatelessWidget {
  final bool compact;
  const UsageBanner({super.key, this.compact = false});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<UsageSnapshot>(
      valueListenable: UsageService.instance.snapshot,
      builder: (context, snap, _) {
        if (snap.tier.tier == AppTier.trial) return const SizedBox.shrink();
        if (compact) return _CompactPill(snap: snap);
        return _FullBanner(snap: snap);
      },
    );
  }
}

class _CompactPill extends StatelessWidget {
  final UsageSnapshot snap;
  const _CompactPill({required this.snap});

  @override
  Widget build(BuildContext context) {
    final cs  = Theme.of(context).colorScheme;
    final low = snap.messagesRemaining <= 10;

    return GestureDetector(
      onTap: () => Navigator.of(context).pushNamed('/paywall'),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: low
              ? cs.errorContainer
              : cs.surfaceVariant.withOpacity(0.6),
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.chat_bubble_outline_rounded,
              size: 12,
              color: low ? cs.error : cs.onSurfaceVariant,
            ),
            const SizedBox(width: 4),
            Text(
              '${snap.messagesRemaining} left',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: low ? cs.error : cs.onSurfaceVariant,
              ),
            ),
            if (snap.tier.hasVoice && snap.voiceMinutesRemaining < 5) ...[
              const SizedBox(width: 8),
              Icon(Icons.mic_rounded, size: 12, color: cs.error),
              const SizedBox(width: 3),
              Text(
                '${snap.voiceMinutesRemaining}m',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: cs.error,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FullBanner extends StatelessWidget {
  final UsageSnapshot snap;
  const _FullBanner({required this.snap});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surfaceVariant.withOpacity(0.4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: cs.outlineVariant.withOpacity(0.4),
          width: 0.5,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '${snap.tier.displayName} plan',
                style: tt.titleSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              Text(
                'This month',
                style: tt.bodySmall?.copyWith(
                  color: cs.onSurface.withOpacity(0.45),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          _UsageMeter(
            icon: Icons.chat_bubble_outline_rounded,
            label: 'Messages',
            used: snap.messagesUsed,
            total: snap.tier.monthlyMessages,
            fraction: snap.messageFraction,
            remaining: snap.messagesRemaining,
            unit: 'messages',
          ),
          if (snap.tier.hasVoice) ...[
            const SizedBox(height: 12),
            _UsageMeter(
              icon: Icons.mic_rounded,
              label: 'Voice',
              used: (snap.voiceSecondsUsed / 60).floor(),
              total: snap.tier.voiceMinutes,
              fraction: snap.voiceFraction,
              remaining: snap.voiceMinutesRemaining,
              unit: 'min',
            ),
          ],
          if (snap.messagesRemaining <= 20 || snap.voiceMinutesRemaining <= 3)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () =>
                      Navigator.of(context).pushNamed('/paywall'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                  ),
                  child: const Text('Upgrade for more'),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _UsageMeter extends StatelessWidget {
  final IconData icon;
  final String label;
  final int used;
  final int total;
  final double fraction;
  final int remaining;
  final String unit;

  const _UsageMeter({
    required this.icon,
    required this.label,
    required this.used,
    required this.total,
    required this.fraction,
    required this.remaining,
    required this.unit,
  });

  @override
  Widget build(BuildContext context) {
    final cs    = Theme.of(context).colorScheme;
    final tt    = Theme.of(context).textTheme;
    final isLow = fraction > 0.8;
    final barColor = isLow ? cs.error : cs.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: cs.onSurface.withOpacity(0.6)),
            const SizedBox(width: 6),
            Text(label, style: tt.bodySmall),
            const Spacer(),
            Text(
              '$used / $total $unit',
              style: tt.bodySmall?.copyWith(
                fontWeight: FontWeight.w600,
                color: isLow ? cs.error : cs.onSurface.withOpacity(0.7),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: fraction,
            minHeight: 5,
            backgroundColor: cs.surfaceVariant,
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
          ),
        ),
        if (isLow)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              '$remaining $unit remaining this month',
              style: tt.bodySmall?.copyWith(
                color: cs.error,
                fontSize: 11,
              ),
            ),
          ),
      ],
    );
  }
}