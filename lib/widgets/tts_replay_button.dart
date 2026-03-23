import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

class TtsReplayButton extends StatefulWidget {
  final TtsSurface surface;
  final Color? iconColor;
  final String tooltip;

  const TtsReplayButton({
    super.key,
    required this.surface,
    this.iconColor,
    this.tooltip = 'Replay last voice',
  });

  @override
  State<TtsReplayButton> createState() => _TtsReplayButtonState();
}

class _TtsReplayButtonState extends State<TtsReplayButton> {
  bool _hasReplay = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final value = OpenAiTtsService.instance.hasReplay(widget.surface);
    if (!mounted) return;
    setState(() => _hasReplay = value);
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: OpenAiTtsService.instance,
      builder: (context, _) {
        final hasReplay = _hasReplay || OpenAiTtsService.instance.hasReplay(widget.surface);
        return IconButton.filledTonal(
          tooltip: widget.tooltip,
          onPressed: !hasReplay
              ? null
              : () async {
                  final ok = await OpenAiTtsService.instance.replayLast(widget.surface);
                  if (!mounted) return;
                  if (!ok) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Nothing ready to replay yet.')),
                    );
                  }
                },
          icon: Icon(Icons.replay_rounded, color: widget.iconColor),
        );
      },
    );
  }
}
