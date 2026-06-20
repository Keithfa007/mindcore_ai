// lib/pages/pressure_valve_screen.dart
//
// The Pressure Valve — emotional release. Write anything, release it, gone.
// Nothing is saved. Ever. Optional AI reflection (one-off, also not saved).

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/env/env.dart';

class PressureValveScreen extends StatefulWidget {
  const PressureValveScreen({super.key});
  @override
  State<PressureValveScreen> createState() => _PressureValveScreenState();
}

class _PressureValveScreenState extends State<PressureValveScreen>
    with TickerProviderStateMixin {
  final _textCtrl = TextEditingController();
  final _focusNode = FocusNode();

  // States: writing → releasing → released → reflecting → reflected
  bool _releasing = false;
  bool _released = false;
  bool _reflecting = false;
  String? _reflection;

  late final AnimationController _dissolveCtrl;
  late final Animation<double> _dissolveFade;
  late final Animation<double> _dissolveScale;
  late final Animation<double> _dissolveBlur;

  @override
  void initState() {
    super.initState();
    _dissolveCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _dissolveFade = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(parent: _dissolveCtrl, curve: const Interval(0.0, 0.8, curve: Curves.easeOut)),
    );
    _dissolveScale = Tween<double>(begin: 1.0, end: 0.92).animate(
      CurvedAnimation(parent: _dissolveCtrl, curve: Curves.easeInOut),
    );
    _dissolveBlur = Tween<double>(begin: 0.0, end: 8.0).animate(
      CurvedAnimation(parent: _dissolveCtrl, curve: const Interval(0.2, 1.0, curve: Curves.easeIn)),
    );
    // Auto-focus the text field
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _dissolveCtrl.dispose();
    _textCtrl.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  Future<void> _release() async {
    if (_textCtrl.text.trim().isEmpty) return;
    HapticFeedback.heavyImpact();
    _focusNode.unfocus();

    setState(() => _releasing = true);
    await _dissolveCtrl.forward();

    // Text is now visually gone — clear it from memory
    final textForReflection = _textCtrl.text;
    _textCtrl.clear();

    setState(() {
      _releasing = false;
      _released = true;
      // Keep text temporarily in case user wants reflection
      _textCtrl.text = textForReflection;
    });
  }

  Future<void> _letItGo() async {
    HapticFeedback.selectionClick();
    _textCtrl.clear(); // Permanently gone
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  Future<void> _reflectOnThis() async {
    HapticFeedback.selectionClick();
    final text = _textCtrl.text;
    _textCtrl.clear(); // Clear immediately — we only use it for the API call

    setState(() => _reflecting = true);

    try {
      final response = await http.post(
        Uri.parse('https://api.openai.com/v1/chat/completions'),
        headers: {
          'Authorization': 'Bearer ${Env.openaiKey}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'model': 'gpt-4o-mini',
          'temperature': 0.6,
          'max_tokens': 250,
          'messages': [
            {
              'role': 'system',
              'content': 'You are a compassionate, honest companion. The user just wrote something '
                  'they needed to release \u2014 raw, unfiltered emotion. They chose to hear a brief '
                  'reflection before letting it go forever. Give ONE short, honest paragraph. '
                  'Do not quote their words back. Do not give advice. Do not list steps. '
                  'Just reflect what you sense underneath their words \u2014 the feeling behind the feeling. '
                  'Be warm but direct. End with one sentence of quiet encouragement. '
                  'Keep it under 80 words.',
            },
            {
              'role': 'user',
              'content': text,
            },
          ],
        }),
      );

      if (!mounted) return;

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final reply = data['choices']?[0]?['message']?['content'] ?? '';
        setState(() {
          _reflecting = false;
          _reflection = reply.toString().trim();
        });
      } else {
        setState(() {
          _reflecting = false;
          _reflection = 'What you wrote took courage. That\u2019s enough for today.';
        });
      }
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _reflecting = false;
        _reflection = 'What you wrote took courage. That\u2019s enough for today.';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final tt = Theme.of(context).textTheme;
    final bottomInset = MediaQuery.of(context).viewInsets.bottom;

    return Theme(
      data: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Colors.transparent,
      ),
      child: Scaffold(
        backgroundColor: Colors.transparent,
      body: AnimatedBackdrop(
        child: SafeArea(
          child: Padding(
            padding: EdgeInsets.fromLTRB(24, 16, 24, bottomInset > 0 ? 12 : 32),
            child: Column(
              children: [
                // ── Top bar ──────────────────────────────────
                Row(
                  children: [
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: Icon(Icons.close_rounded, size: 22,
                          color: Colors.white.withValues(alpha: 0.40)),
                    ),
                    const Spacer(),
                    Text('Nothing is saved',
                        style: tt.labelSmall?.copyWith(
                          color: Colors.white.withValues(alpha: 0.25),
                          letterSpacing: 0.5,
                        )),
                    const Spacer(),
                    const SizedBox(width: 48), // balance close button
                  ],
                ),
                const SizedBox(height: 12),

                // ── Content area ─────────────────────────────
                if (!_released && !_reflecting && _reflection == null)
                  _buildWritingState(tt, bottomInset)
                else if (_released && !_reflecting && _reflection == null)
                  _buildReleasedState(tt)
                else if (_reflecting)
                  _buildReflectingState(tt)
                else
                  _buildReflectionState(tt),
              ],
            ),
          ),
        ),
      ),
    ),
    );
  }

  // ── Writing state ───────────────────────────────────────────────
  Widget _buildWritingState(TextTheme tt, double bottomInset) {
    return Expanded(
      child: Column(
        children: [
          const Spacer(),
          Icon(Icons.water_drop_outlined,
              color: AppColors.primary.withValues(alpha: 0.30), size: 36),
          const SizedBox(height: 16),
          Text(
            'Say everything you need to say.',
            textAlign: TextAlign.center,
            style: tt.titleLarge?.copyWith(
              fontWeight: FontWeight.w900,
              letterSpacing: -0.5,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Nobody will ever read this.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.35),
            ),
          ),
          const SizedBox(height: 24),

          // ── Text field with dissolve animation ──
          Expanded(
            child: AnimatedBuilder(
              animation: _dissolveCtrl,
              builder: (context, child) {
                return Opacity(
                  opacity: _releasing ? _dissolveFade.value : 1.0,
                  child: Transform.scale(
                    scale: _releasing ? _dissolveScale.value : 1.0,
                    child: child,
                  ),
                );
              },
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.04),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.08),
                  ),
                ),
                child: TextField(
                  controller: _textCtrl,
                  focusNode: _focusNode,
                  maxLines: null,
                  expands: true,
                  textAlignVertical: TextAlignVertical.top,
                  style: tt.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.85),
                    height: 1.6,
                  ),
                  decoration: InputDecoration(
                    hintText: 'Let it out\u2026',
                    hintStyle: tt.bodyLarge?.copyWith(
                      color: Colors.white.withValues(alpha: 0.18),
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    fillColor: Colors.transparent,
                    filled: true,
                    contentPadding: EdgeInsets.zero,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // ── Release button ──
          if (!_releasing)
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _textCtrl.text.trim().isEmpty ? null : _release,
                style: FilledButton.styleFrom(
                  backgroundColor: const Color(0xFFE24B4A),
                  disabledBackgroundColor: const Color(0xFFE24B4A).withValues(alpha: 0.20),
                  minimumSize: const Size.fromHeight(52),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: Text('Release',
                    style: tt.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w800,
                    )),
              ),
            ),
        ],
      ),
    );
  }

  // ── Released state (text dissolved, choose next action) ─────────
  Widget _buildReleasedState(TextTheme tt) {
    return Expanded(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Spacer(flex: 2),
          Icon(Icons.check_circle_outline_rounded,
              color: AppColors.mintDeep, size: 48),
          const SizedBox(height: 20),
          Text(
            'Released.',
            style: tt.headlineSmall?.copyWith(
              fontWeight: FontWeight.w900,
              color: Colors.white,
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Those words are gone. They can\u2019t weigh you down anymore.',
            textAlign: TextAlign.center,
            style: tt.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.50),
              height: 1.5,
            ),
          ),
          const Spacer(flex: 2),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _reflectOnThis,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                minimumSize: const Size.fromHeight(52),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text('Reflect on this',
                  style: tt.titleMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  )),
            ),
          ),
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton(
              onPressed: _letItGo,
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
                side: BorderSide(
                  color: Colors.white.withValues(alpha: 0.15),
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text('Let it go',
                  style: tt.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: Colors.white.withValues(alpha: 0.55),
                  )),
            ),
          ),
        ],
      ),
    );
  }

  // ── Reflecting state (loading) ──────────────────────────────────
  Widget _buildReflectingState(TextTheme tt) {
    return Expanded(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 32, height: 32,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: AppColors.primary.withValues(alpha: 0.60),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Listening\u2026',
            style: tt.bodyMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.40),
            ),
          ),
        ],
      ),
    );
  }

  // ── Reflection shown ────────────────────────────────────────────
  Widget _buildReflectionState(TextTheme tt) {
    return Expanded(
      child: Column(
        children: [
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppColors.primary.withValues(alpha: 0.15),
              ),
            ),
            child: Column(
              children: [
                Icon(Icons.format_quote_rounded,
                    color: AppColors.primary.withValues(alpha: 0.30), size: 28),
                const SizedBox(height: 14),
                Text(
                  _reflection ?? '',
                  textAlign: TextAlign.center,
                  style: tt.bodyLarge?.copyWith(
                    color: Colors.white.withValues(alpha: 0.80),
                    height: 1.6,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'This reflection will not be saved.',
            textAlign: TextAlign.center,
            style: tt.bodySmall?.copyWith(
              color: Colors.white.withValues(alpha: 0.20),
            ),
          ),
          const Spacer(),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: () {
                HapticFeedback.selectionClick();
                Navigator.of(context).pop();
              },
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primary,
                minimumSize: const Size.fromHeight(52),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              child: Text('Done',
                  style: tt.titleMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  )),
            ),
          ),
        ],
      ),
    );
  }
}
