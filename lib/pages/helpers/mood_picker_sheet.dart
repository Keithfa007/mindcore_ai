import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/mood_log_service.dart';

class MoodPickerSheet extends StatelessWidget {
  const MoodPickerSheet({super.key});

  @override
  Widget build(BuildContext context) {
    final moods = const [
      {'emoji': '😌', 'label': 'Calm'},
      {'emoji': '😊', 'label': 'Happy'},
      {'emoji': '🙂', 'label': 'Neutral'},
      {'emoji': '😔', 'label': 'Low'},
      {'emoji': '😤', 'label': 'Frustrated'},
      {'emoji': '😟', 'label': 'Anxious'},
    ];

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade400,
                borderRadius: BorderRadius.circular(2),
              ),
              margin: const EdgeInsets.only(bottom: 12),
            ),
            const Text(
              'How are you feeling?',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: moods.map((m) {
                final emoji = m['emoji'] as String;
                final label = m['label'] as String;

                return InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onTap: () async {
                    // 1️⃣ Save mood (local + Firestore attempt)
                    final cloudOk = await MoodLogService.logMood(
                      emoji: emoji,
                      label: label,
                    );

                    if (!context.mounted) return;

                    // 2️⃣ Show result to user
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          cloudOk
                              ? '✅ Mood saved to cloud'
                              : '⚠️ Mood saved locally only',
                        ),
                        duration: const Duration(seconds: 2),
                      ),
                    );

                    // 3️⃣ Close sheet
                    Navigator.pop(context);
                  },
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(emoji, style: const TextStyle(fontSize: 20)),
                        const SizedBox(width: 8),
                        Text(label),
                      ],
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
          ],
        ),
      ),
    );
  }
}
