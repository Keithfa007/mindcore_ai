import 'dart:math' as math;
import 'package:flutter/material.dart';

class AiSpeakingWave extends StatefulWidget {
  final bool active;
  final double height;

  const AiSpeakingWave({
    super.key,
    required this.active,
    this.height = 28,
  });

  @override
  State<AiSpeakingWave> createState() => _AiSpeakingWaveState();
}

class _AiSpeakingWaveState extends State<AiSpeakingWave>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    );
    if (widget.active) {
      _controller.repeat();
    }
  }

  @override
  void didUpdateWidget(covariant AiSpeakingWave oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.active && !_controller.isAnimating) {
      _controller.repeat();
    } else if (!widget.active && _controller.isAnimating) {
      _controller.stop();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return SizedBox(
          height: widget.height,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: List.generate(5, (index) {
              final t = _controller.value * math.pi * 2;
              final phase = t + (index * 0.7);
              final factor = widget.active ? (0.25 + ((math.sin(phase) + 1) / 2) * 0.75) : 0.2;
              final barHeight = 6 + (widget.height - 6) * factor;
              return Container(
                width: 4,
                height: barHeight,
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: widget.active ? 0.95 : 0.35),
                  borderRadius: BorderRadius.circular(999),
                ),
              );
            }),
          ),
        );
      },
    );
  }
}
