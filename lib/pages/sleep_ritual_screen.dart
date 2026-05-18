// lib/pages/sleep_ritual_screen.dart
import 'package:flutter/material.dart';
import 'package:mindcore_ai/services/sleep_ritual_service.dart';

enum SleepRitualMode { evening, morning }

class SleepRitualScreen extends StatefulWidget {
  final SleepRitualMode mode;
  const SleepRitualScreen({super.key, required this.mode});

  @override
  State<SleepRitualScreen> createState() => _SleepRitualScreenState();
}

class _SleepRitualScreenState extends State<SleepRitualScreen>
    with SingleTickerProviderStateMixin {
  int?   _selected;
  String _note            = '';
  bool   _saving          = false;
  bool   _done            = false;
  int?   _lastNightScore;

  late AnimationController _doneController;
  late Animation<double>   _doneScale;

  @override
  void initState() {
    super.initState();
    _doneController = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 500));
    _doneScale = Tween<double>(begin: 0.5, end: 1.0).animate(
        CurvedAnimation(parent: _doneController, curve: Curves.elasticOut));
    if (widget.mode == SleepRitualMode.morning) _loadLastNight();
  }

  @override
  void dispose() {
    _doneController.dispose();
    super.dispose();
  }

  Future<void> _loadLastNight() async {
    final data = await SleepRitualService.instance.getLastNightCheckIn();
    if (!mounted) return;
    setState(() => _lastNightScore = data?['eveningScore'] as int?);
  }

  Future<void> _submit() async {
    if (_selected == null || _saving) return;
    setState(() => _saving = true);
    if (widget.mode == SleepRitualMode.evening) {
      await SleepRitualService.instance.saveEveningCheckIn(
          score: _selected!, note: _note.trim().isEmpty ? null : _note.trim());
    } else {
      await SleepRitualService.instance.saveMorningCheckIn(
          score: _selected!, note: _note.trim().isEmpty ? null : _note.trim());
    }
    if (!mounted) return;
    setState(() { _saving = false; _done = true; });
    _doneController.forward();
    await Future.delayed(const Duration(milliseconds: 1200));
    if (mounted) Navigator.of(context).pop();
  }

  // ── Colours ───────────────────────────────────────────────────────────

  Color _scoreColor(int score) {
    if (score <= 3) return const Color(0xFFE57373);
    if (score <= 6) return const Color(0xFFE8A265);
    return const Color(0xFF4CAF82);
  }

  String _scoreMeaning(int score) {
    if (score <= 3) return 'Tough';
    if (score <= 6) return 'Mixed';
    return 'Good';
  }

  // ── UI ────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final isEvening = widget.mode == SleepRitualMode.evening;
    final theme     = Theme.of(context);
    final isDark    = theme.brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0A0E1A) : const Color(0xFFF5F7FF),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new,
              color: isDark ? Colors.white54 : Colors.black45),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: _done ? _buildDoneState() : _buildForm(isEvening, isDark),
      ),
    );
  }

  Widget _buildDoneState() {
    return Center(
      child: ScaleTransition(
        scale: _doneScale,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: const Color(0xFF4CAF82).withValues(alpha: 0.15),
                border: Border.all(color: const Color(0xFF4CAF82), width: 2),
              ),
              child: const Icon(Icons.check_rounded,
                  color: Color(0xFF4CAF82), size: 42),
            ),
            const SizedBox(height: 16),
            const Text('Checked in',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          ],
        ),
      ),
    );
  }

  Widget _buildForm(bool isEvening, bool isDark) {
    final labelColor = isDark ? Colors.white70 : Colors.black87;
    final subtleColor = isDark
        ? Colors.white.withValues(alpha: 0.40)
        : Colors.black.withValues(alpha: 0.40);

    return ListView(
      padding: const EdgeInsets.fromLTRB(28, 8, 28, 40),
      children: [
        const SizedBox(height: 16),

        // Greeting
        Text(
          isEvening ? 'Good evening \ud83c\udf19' : 'Good morning \u2600\ufe0f',
          style: TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: labelColor),
        ),
        const SizedBox(height: 12),

        // Subtext
        if (isEvening)
          Text('How did today go?',
              style: TextStyle(fontSize: 17, color: subtleColor))
        else ...[    
          if (_lastNightScore != null) ...[
            RichText(text: TextSpan(
              style: TextStyle(fontSize: 16, color: subtleColor),
              children: [
                const TextSpan(text: 'Last night you were at a '),
                TextSpan(
                  text: '$_lastNightScore',
                  style: TextStyle(
                      color: _scoreColor(_lastNightScore!),
                      fontWeight: FontWeight.w800,
                      fontSize: 18),
                ),
                const TextSpan(text: '.'),
              ],
            )),
            const SizedBox(height: 6),
          ],
          Text('How are you feeling now?',
              style: TextStyle(fontSize: 17, color: subtleColor)),
        ],

        const SizedBox(height: 40),

        // Score grid
        _buildScoreGrid(isDark),

        const SizedBox(height: 8),

        // Score meaning label
        if (_selected != null)
          Center(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 200),
              child: Text(
                _scoreMeaning(_selected!),
                key: ValueKey(_selected),
                style: TextStyle(
                    color: _scoreColor(_selected!),
                    fontWeight: FontWeight.w700,
                    fontSize: 14),
              ),
            ),
          ),

        const SizedBox(height: 32),

        // Optional note
        TextField(
          onChanged: (v) => _note = v,
          maxLines: 2,
          maxLength: 120,
          style: TextStyle(color: labelColor, fontSize: 15),
          decoration: InputDecoration(
            hintText: 'One word or one sentence\u2026 (optional)',
            hintStyle: TextStyle(color: subtleColor, fontSize: 14),
            counterStyle: TextStyle(color: subtleColor, fontSize: 11),
            filled: true,
            fillColor: isDark
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.black.withValues(alpha: 0.04),
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide.none),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          ),
        ),

        const SizedBox(height: 28),

        // Submit
        SizedBox(
          height: 52,
          child: FilledButton(
            onPressed: _selected == null || _saving ? null : _submit,
            style: FilledButton.styleFrom(
              backgroundColor: _selected != null
                  ? _scoreColor(_selected!)
                  : (isDark
                      ? Colors.white.withValues(alpha: 0.12)
                      : Colors.black.withValues(alpha: 0.08)),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14)),
            ),
            child: _saving
                ? const SizedBox(
                    width: 22, height: 22,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white))
                : const Text('Check in',
                    style: TextStyle(
                        fontWeight: FontWeight.w800, fontSize: 16)),
          ),
        ),
      ],
    );
  }

  Widget _buildScoreGrid(bool isDark) {
    // Two rows: 1-5 and 6-10
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(5, (i) => _scoreCircle(i + 1, isDark)),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(5, (i) => _scoreCircle(i + 6, isDark)),
        ),
      ],
    );
  }

  Widget _scoreCircle(int n, bool isDark) {
    final selected = _selected == n;
    final color    = _scoreColor(n);
    return GestureDetector(
      onTap: () => setState(() => _selected = n),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        width:  selected ? 52 : 44,
        height: selected ? 52 : 44,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color:  selected ? color.withValues(alpha: 0.20) : Colors.transparent,
          border: Border.all(
            color:  selected ? color : (isDark
                ? Colors.white.withValues(alpha: 0.18)
                : Colors.black.withValues(alpha: 0.15)),
            width: selected ? 2.5 : 1.5,
          ),
          boxShadow: selected
              ? [BoxShadow(
                  color: color.withValues(alpha: 0.30),
                  blurRadius: 12, spreadRadius: 2)]
              : [],
        ),
        child: Center(
          child: Text(
            '$n',
            style: TextStyle(
              fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
              fontSize:   selected ? 17 : 15,
              color: selected
                  ? color
                  : (isDark
                      ? Colors.white.withValues(alpha: 0.60)
                      : Colors.black.withValues(alpha: 0.55)),
            ),
          ),
        ),
      ),
    );
  }
}
