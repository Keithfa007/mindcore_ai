import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';

class TtsSpeakerButton extends StatelessWidget {
  final String text;
  final String? messageId;
  final String moodLabel;
  final TtsSurface surface;
  final bool force;
  final String tooltipSpeak;
  final String tooltipStop;
  final Color? iconColor;

  const TtsSpeakerButton({
    super.key,
    required this.text,
    required this.surface,
    this.messageId,
    this.moodLabel = 'calm',
    this.force = true,
    this.tooltipSpeak = 'Read aloud',
    this.tooltipStop = 'Stop voice',
    this.iconColor,
  });

  @override
  Widget build(BuildContext context) {
    final resolvedMessageId = messageId ?? '${surface.name}_${text.hashCode}';
    return AnimatedBuilder(
      animation: OpenAiTtsService.instance,
      builder: (context, _) {
        final isActive = OpenAiTtsService.instance.isSpeakingMessage(resolvedMessageId);
        return IconButton.filledTonal(
          tooltip: isActive ? tooltipStop : tooltipSpeak,
          onPressed: text.trim().isEmpty
              ? null
              : () async {
                  if (isActive) {
                    await OpenAiTtsService.instance.stop();
                    return;
                  }
                  await OpenAiTtsService.instance.speak(
                    text,
                    moodLabel: moodLabel,
                    surface: surface,
                    force: force,
                    messageId: resolvedMessageId,
                  );
                },
          icon: Icon(
            isActive ? Icons.stop_rounded : Icons.volume_up_rounded,
            color: iconColor,
          ),
        );
      },
    );
  }
}
