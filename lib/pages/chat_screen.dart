// lib/pages/chat_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';
import 'package:uuid/uuid.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:firebase_auth/firebase_auth.dart';

import 'package:mindcore_ai/models/chat_message.dart';
import 'package:mindcore_ai/models/conversation_meta.dart';
import 'package:mindcore_ai/ai/agent_action.dart';
import 'package:mindcore_ai/ai/agent_type.dart';
import 'package:mindcore_ai/ai/proactive_support_service.dart';
import 'package:mindcore_ai/pages/helpers/chat_persistence.dart';

import 'package:mindcore_ai/services/mood_log_service.dart';
import 'package:mindcore_ai/pages/helpers/mood_suggester.dart';

import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/openai_tts_service.dart';
import 'package:mindcore_ai/services/chat_stream_service.dart';
import 'package:mindcore_ai/services/therapist_mode_service.dart';

import 'package:mindcore_ai/services/usage_service.dart';
import 'package:mindcore_ai/widgets/usage_banner.dart';

import 'helpers/mood_picker_sheet.dart';

import 'package:mindcore_ai/widgets/gradient_background.dart';
import 'package:mindcore_ai/widgets/app_top_bar.dart';
import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/disclaimer_banner.dart';
import 'package:mindcore_ai/pages/helpers/route_observer.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> with AutoStopTtsRouteAware<ChatScreen> {
  final _id = const Uuid();
  final _controller = TextEditingController();
  final _composerFocus = FocusNode();
  final _scroll = ScrollController();

  String _currentConvId = "";
  List<ConversationMeta> _convs = [];

  String? _currentMoodEmoji;
  String _currentMoodLabel = 'Neutral';

  final List<ChatMessage> _messages = [];
  bool _isSending = false;
  bool _isTyping = false;
  bool _showResetNudge = false;
  List<SupportPromptChip> _quickPrompts = const [];

  MoodSuggestion? _pendingMood;
  bool _showMoodSuggestion = false;
  int _turnsSinceMoodPrompt = 0;

  static const double _autoLogMinConfidence = 0.78;
  static const double _suggestMinConfidence = 0.58;

  static const String _kAutoMoodLastTs    = 'auto_mood_last_ts';
  static const String _kAutoMoodLastLabel = 'auto_mood_last_label';
  static const String _kManualMoodLastTs  = 'manual_mood_last_ts';

  bool _ttsEnabled = true;
  bool _didHandleRouteArgs = false;

  static const String? kBotLogoAsset = 'assets/images/logo512.png';
  TherapistModeConfig _therapistMode = TherapistModeConfig.fallback;

  @override
  void initState() {
    super.initState();
    _composerFocus.addListener(() {
      if (_composerFocus.hasFocus) _scheduleScrollToBottom(animated: false);
    });
    _boot();
  }

  Future<void> _boot() async {
    await OpenAiTtsService.instance.init();
    _ttsEnabled = await OpenAiTtsService.instance.getSurfaceEnabled(TtsSurface.chat);
    _therapistMode = await TherapistModeService.load();

    final id = await ChatPersistence.ensureDefault();
    await _refreshQuickPrompts();
    _currentConvId = id;
    _convs = await ChatPersistence.listConversations();
    final saved = await ChatPersistence.load(_currentConvId);

    if (!mounted) return;
    setState(() {
      _messages..clear()..addAll(saved);
      _pendingMood = null;
      _showMoodSuggestion = false;
      _turnsSinceMoodPrompt = 0;
    });
    await _refreshQuickPrompts();
    _scheduleScrollToBottom(animated: false);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_didHandleRouteArgs) return;
    _didHandleRouteArgs = true;

    final args = ModalRoute.of(context)?.settings.arguments;
    if (args is! Map) return;

    final prefillText = args['prefillText']?.toString();
    final autoSend    = args['autoSend'] == true;
    if (prefillText == null || prefillText.trim().isEmpty) return;

    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _controller.text = prefillText.trim();
      _controller.selection =
          TextSelection.fromPosition(TextPosition(offset: _controller.text.length));
      setState(() {});
      if (autoSend && !_isSending) unawaited(_send());
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _composerFocus.dispose();
    _scroll.dispose();
    OpenAiTtsService.instance.stop();
    super.dispose();
  }

  // ---------- Conversation management ----------

  Future<void> _newConversation() async {
    if (_isSending) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please wait for the reply to finish…')));
      return;
    }
    if (LiveVoicePreferences.instance.interruptOnNewMessage) {
      await _stopSpeech(resetState: true);
    }
    final newId = "conv-${DateTime.now().millisecondsSinceEpoch}";
    final meta = await ChatPersistence.createConversation(
        id: newId, title: "Chat ${_convs.length + 1}");
    _convs = await ChatPersistence.listConversations();
    await ChatPersistence.save(newId, const []);
    if (!mounted) return;
    setState(() {
      _currentConvId = meta.id;
      _messages.clear();
      _pendingMood = null;
      _showMoodSuggestion = false;
      _turnsSinceMoodPrompt = 0;
    });
    await _refreshQuickPrompts();
  }

  Future<void> _switchConversation(String convId) async {
    await _stopSpeech(resetState: true);
    final msgs = await ChatPersistence.load(convId);
    _convs = await ChatPersistence.listConversations();
    if (!mounted) return;
    setState(() {
      _currentConvId = convId;
      _messages..clear()..addAll(msgs);
      _pendingMood = null;
      _showMoodSuggestion = false;
      _turnsSinceMoodPrompt = 0;
    });
    await _refreshQuickPrompts();
    _scheduleScrollToBottom(animated: false);
  }

  Future<void> _renameConversation() async {
    final current = _convs.firstWhere((c) => c.id == _currentConvId,
        orElse: () => ConversationMeta(id: _currentConvId, title: "Chat"));
    final controller = TextEditingController(text: current.title);
    final newTitle = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Rename chat'),
        content: TextField(controller: controller, autofocus: true),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, controller.text.trim()),
              child: const Text('Save')),
        ],
      ),
    );
    if (newTitle == null || newTitle.isEmpty) return;
    await ChatPersistence.renameConversation(id: _currentConvId, title: newTitle);
    _convs = await ChatPersistence.listConversations();
    if (!mounted) return;
    setState(() {});
  }

  Future<void> _deleteConversation() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete chat?'),
        content: const Text('This will permanently remove the conversation.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (confirm != true) return;
    await _stopSpeech(resetState: true);
    await ChatPersistence.deleteConversation(_currentConvId);
    _convs = await ChatPersistence.listConversations();
    _currentConvId = _convs.isEmpty
        ? await ChatPersistence.ensureDefault()
        : _convs.first.id;
    final msgs = await ChatPersistence.load(_currentConvId);
    if (!mounted) return;
    setState(() {
      _messages..clear()..addAll(msgs);
      _pendingMood = null;
      _showMoodSuggestion = false;
      _turnsSinceMoodPrompt = 0;
    });
  }

  Future<void> _clearHistory() async {
    if (_currentConvId.isEmpty) return;
    await _stopSpeech(resetState: true);
    await ChatPersistence.clear(_currentConvId);
    if (!mounted) return;
    setState(() {
      _messages.clear();
      _pendingMood = null;
      _showMoodSuggestion = false;
      _turnsSinceMoodPrompt = 0;
    });
    await _refreshQuickPrompts();
  }

  // ---------- Mood logging ----------

  Future<void> _onLogMoodPressed() async {
    final picked = await _showMoodPicker();
    if (picked == null) return;
    final emoji = picked['emoji']!;
    final label = picked['label']!;
    await MoodLogService.logMood(emoji: emoji, label: label);
    await _markManualLogged();
    if (!mounted) return;
    setState(() {
      _currentMoodEmoji = emoji;
      _currentMoodLabel = label;
      _pendingMood = null;
      _showMoodSuggestion = false;
    });
    await _refreshQuickPrompts();
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('Mood logged: $emoji $label')));
  }

  Future<Map<String, String>?> _showMoodPicker() async {
    final res = await showModalBottomSheet<dynamic>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => const MoodPickerSheet(),
    );
    if (res == null) return null;
    if (res is Map) {
      return {
        'emoji': (res['emoji'] ?? '🙂').toString(),
        'label': (res['label'] ?? 'Neutral').toString(),
      };
    }
    return null;
  }

  Future<void> _markManualLogged() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kManualMoodLastTs, DateTime.now().millisecondsSinceEpoch);
  }

  Future<bool> _canAutoLog(String label) async {
    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    final manualTsMs = prefs.getInt(_kManualMoodLastTs) ?? 0;
    if (manualTsMs > 0) {
      final manualTs = DateTime.fromMillisecondsSinceEpoch(manualTsMs);
      if (now.difference(manualTs).inHours < 3) return false;
    }
    final lastAutoMs = prefs.getInt(_kAutoMoodLastTs) ?? 0;
    if (lastAutoMs > 0) {
      final lastAuto = DateTime.fromMillisecondsSinceEpoch(lastAutoMs);
      if (now.difference(lastAuto).inHours < 6) return false;
    }
    final lastLabel = prefs.getString(_kAutoMoodLastLabel) ?? '';
    if (lastAutoMs > 0 && lastLabel.toLowerCase() == label.toLowerCase()) {
      final lastAuto = DateTime.fromMillisecondsSinceEpoch(lastAutoMs);
      if (now.difference(lastAuto).inHours < 12) return false;
    }
    return true;
  }

  Future<void> _markAutoLogged(String label) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kAutoMoodLastTs, DateTime.now().millisecondsSinceEpoch);
    await prefs.setString(_kAutoMoodLastLabel, label);
  }

  Future<void> _handleMoodFromConversation(
      {required String userText, required String botText}) async {
    _turnsSinceMoodPrompt++;
    if (_turnsSinceMoodPrompt < 2) return;
    _turnsSinceMoodPrompt = 0;
    final suggestion = MoodSuggester.suggest(userText: userText, botText: botText);
    if (suggestion.confidence >= _autoLogMinConfidence) {
      final ok = await _canAutoLog(suggestion.label);
      if (!ok) return;
      await MoodLogService.logMood(
          emoji: suggestion.emoji, label: suggestion.label, note: 'Auto (chat)');
      await _markAutoLogged(suggestion.label);
      if (!mounted) return;
      setState(() {
        _currentMoodEmoji = suggestion.emoji;
        _currentMoodLabel = suggestion.label;
        _pendingMood = null;
        _showMoodSuggestion = false;
      });
      await _refreshQuickPrompts();
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Mood auto-logged: ${suggestion.emoji} ${suggestion.label}')));
      return;
    }
    if (suggestion.confidence >= _suggestMinConfidence) {
      if (!mounted) return;
      setState(() {
        _pendingMood = suggestion;
        _showMoodSuggestion = true;
      });
    }
  }

  void _persist({String? convId}) {
    final id = convId ?? _currentConvId;
    if (id.isEmpty) return;
    ChatPersistence.save(id, _messages);
  }

  Future<void> _jumpToBottom({bool animated = true}) async {
    await Future.delayed(const Duration(milliseconds: 20));
    if (!_scroll.hasClients) return;
    final offset = _scroll.position.maxScrollExtent;
    if (animated) {
      await _scroll.animateTo(offset,
          duration: const Duration(milliseconds: 220), curve: Curves.easeOutCubic);
    } else {
      _scroll.jumpTo(offset);
    }
  }

  void _scheduleScrollToBottom({bool animated = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      unawaited(_jumpToBottom(animated: animated));
      Future.delayed(const Duration(milliseconds: 80),
          () { if (!mounted) return; unawaited(_jumpToBottom(animated: false)); });
      Future.delayed(const Duration(milliseconds: 220),
          () { if (!mounted) return; unawaited(_jumpToBottom(animated: false)); });
    });
  }

  Future<void> _stopSpeech({bool resetState = false}) async {
    await OpenAiTtsService.instance.stop();
    if (!mounted || !resetState) return;
    setState(() {});
  }

  Future<void> _logSuggestedMood() async {
    final s = _pendingMood;
    if (s == null) return;
    await MoodLogService.logMood(emoji: s.emoji, label: s.label);
    await _markManualLogged();
    if (!mounted) return;
    setState(() {
      _currentMoodEmoji = s.emoji;
      _currentMoodLabel = s.label;
      _pendingMood = null;
      _showMoodSuggestion = false;
    });
    await _refreshQuickPrompts();
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('Mood logged: ${s.emoji} ${s.label}')));
  }

  Future<void> _changeMoodAndLog() async {
    final picked = await _showMoodPicker();
    if (picked == null) return;
    await MoodLogService.logMood(emoji: picked['emoji']!, label: picked['label']!);
    await _markManualLogged();
    if (!mounted) return;
    setState(() {
      _currentMoodEmoji = picked['emoji']!;
      _currentMoodLabel = picked['label']!;
      _pendingMood = null;
      _showMoodSuggestion = false;
    });
    await _refreshQuickPrompts();
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Mood logged: ${picked['emoji']} ${picked['label']}')));
  }

  Future<void> _refreshQuickPrompts() async {
    final unifiedSuggestion = await ProactiveSupportService.buildHomeSuggestion();
    if (!mounted) return;
    setState(() {
      _quickPrompts = ProactiveSupportService.buildChatPromptChips(
        moodLabel: _currentMoodLabel,
        isEvening: DateTime.now().hour >= 20 || DateTime.now().hour < 5,
        hasMessages: _messages.isNotEmpty,
        unifiedSuggestion: unifiedSuggestion,
      );
    });
  }

  void _applyPromptChip(SupportPromptChip chip) {
    if (chip.routeName != null) {
      Navigator.of(context).pushNamed(chip.routeName!, arguments: chip.routeArguments);
      return;
    }
    _controller.text = chip.promptText;
    _controller.selection =
        TextSelection.fromPosition(TextPosition(offset: _controller.text.length));
    if (chip.autoSend) {
      unawaited(_send());
    } else {
      setState(() {});
    }
  }

  Widget _buildTherapistModeChip() {
    if (!_therapistMode.enabled) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(999),
          ),
          child: Text(
            'Therapist mode: ${_therapistMode.modeLabel}',
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w700,
                  color: Theme.of(context).colorScheme.primary,
                ),
          ),
        ),
      ),
    );
  }

  Widget _buildMoodSuggestionBar() {
    if (!_showMoodSuggestion || _pendingMood == null) return const SizedBox.shrink();
    final s = _pendingMood!;
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      child: GlassCard(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Text(s.emoji, style: const TextStyle(fontSize: 18)),
              const SizedBox(width: 10),
              Expanded(
                  child: Text('Log mood: ${s.label}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                      overflow: TextOverflow.ellipsis)),
              TextButton(onPressed: _logSuggestedMood, child: const Text('Log')),
              TextButton(onPressed: _changeMoodAndLog, child: const Text('Change')),
              IconButton(
                  onPressed: () => setState(() => _showMoodSuggestion = false),
                  icon: const Icon(Icons.close, size: 18),
                  tooltip: 'Not now'),
            ],
          ),
        ),
      ),
    );
  }

  // ---------- Send ----------

  Future<void> _send() async {
    final text = _controller.text.trim();
    _showResetNudge = _shouldShowResetNudge(text);
    if (text.isEmpty || _isSending) return;

    final allowed = await UsageService.instance.tryConsumeMessage(context);
    if (!allowed) return;

    await _stopSpeech(resetState: true);
    final convIdAtSend = _currentConvId;

    final userMsg = ChatMessage(
        id: _id.v4(), role: 'user', text: text, timestamp: DateTime.now());

    if (_currentConvId != convIdAtSend) return;
    setState(() => _messages.add(userMsg));
    await _refreshQuickPrompts();
    _controller.clear();
    _persist(convId: convIdAtSend);
    _scheduleScrollToBottom(animated: true);

    if (_messages.where((m) => m.role == 'user').length == 1) {
      await ChatPersistence.autoTitleIfUntitled(id: convIdAtSend, seed: text);
      _convs = await ChatPersistence.listConversations();
      if (mounted && _currentConvId == convIdAtSend) setState(() {});
    }

    setState(() { _isSending = true; _isTyping = true; });

    try {
      final recent = _messages.length > 9
          ? _messages.sublist(_messages.length - 9)
          : List<ChatMessage>.from(_messages);
      final history =
          recent.map((m) => {"role": m.role, "content": m.text}).toList();
      if (history.isNotEmpty &&
          history.last["role"] == "user" &&
          history.last["content"] == text) {
        history.removeLast();
      }
      final asstId = _id.v4();
      if (_currentConvId != convIdAtSend) return;

      setState(() {
        _messages.add(ChatMessage(
            id: asstId, role: 'assistant', text: '', timestamp: DateTime.now()));
      });
      await _refreshQuickPrompts();
      _persist(convId: convIdAtSend);
      _scheduleScrollToBottom(animated: false);

      final result = await ChatStreamService.streamOrchestratedReply(
        history: history,
        moodLabel: _currentMoodLabel,
        userInput: text,
        screen: 'chat',
        onDelta: (delta) async {
          if (!mounted || _currentConvId != convIdAtSend) return;
          final idx = _messages.indexWhere((m) => m.id == asstId);
          if (idx == -1) return;
          final existing = _messages[idx];
          _messages[idx] = existing.copyWith(text: existing.text + delta);
          if (mounted) { setState(() {}); _scheduleScrollToBottom(animated: false); }
        },
      );

      final finalIdx = _messages.indexWhere((m) => m.id == asstId);
      if (finalIdx != -1) {
        _messages[finalIdx] = _messages[finalIdx].copyWith(
          routedAgent: result.agent.key,
          supportModeLabel: result.supportModeLabel,
          suggestedActions: result.suggestedActions,
        );
        setState(() {});
      }
      await _refreshQuickPrompts();
      _persist(convId: convIdAtSend);
      _scheduleScrollToBottom(animated: false);

      if (_ttsEnabled && mounted && _currentConvId == convIdAtSend) {
        await OpenAiTtsService.instance.speak(result.reply,
            moodLabel: _currentMoodLabel,
            messageId: asstId,
            surface: TtsSurface.chat);
      }

      if (mounted && _currentConvId == convIdAtSend) {
        await _handleMoodFromConversation(userText: text, botText: result.reply);
      }
    } catch (e) {
      if (mounted && _currentConvId == convIdAtSend) {
        setState(() {
          _messages.add(ChatMessage(
            id: _id.v4(),
            role: 'assistant',
            text: "⚠️ I couldn't reach the AI right now.\n"
                "Please check your internet connection and API key configuration.\n\nError: $e",
            timestamp: DateTime.now(),
            supportModeLabel: 'Connection issue',
          ));
        });
      }
    } finally {
      if (mounted && _currentConvId == convIdAtSend) {
        setState(() { _isSending = false; _isTyping = false; });
        _persist(convId: convIdAtSend);
        _scheduleScrollToBottom(animated: false);
      }
    }
  }

  Future<void> _retryAssistantMessage(String messageId) async {
    if (_isSending) return;
    final idx = _messages.indexWhere(
        (m) => m.id == messageId && m.role == 'assistant');
    if (idx == -1) return;
    if (LiveVoicePreferences.instance.interruptOnNewMessage) {
      await _stopSpeech(resetState: true);
    }
    int u = idx - 1;
    while (u >= 0 && _messages[u].role != 'user') u--;
    if (u < 0) return;
    final userMsg = _messages[u];
    final convIdAtSend = _currentConvId;
    setState(() {
      _messages[idx] = _messages[idx].copyWith(
          text: '', timestamp: DateTime.now(),
          routedAgent: '', supportModeLabel: '', suggestedActions: const []);
      _isSending = true; _isTyping = true;
    });
    _persist(convId: convIdAtSend);
    try {
      final slice = _messages.take(u + 1).toList();
      final recent = slice.length > 9 ? slice.sublist(slice.length - 9) : List<ChatMessage>.from(slice);
      final history = recent.map((m) => {"role": m.role, "content": m.text}).toList();
      if (history.isNotEmpty && history.last["role"] == "user" && history.last["content"] == userMsg.text) {
        history.removeLast();
      }
      final result = await ChatStreamService.streamOrchestratedReply(
        history: history,
        moodLabel: _currentMoodLabel,
        userInput: userMsg.text,
        screen: 'chat',
        onDelta: (delta) async {
          if (!mounted || _currentConvId != convIdAtSend) return;
          final ci = _messages.indexWhere((m) => m.id == messageId);
          if (ci == -1) return;
          final existing = _messages[ci];
          _messages[ci] = existing.copyWith(text: existing.text + delta);
          if (mounted) { setState(() {}); _scheduleScrollToBottom(animated: false); }
        },
      );
      final curIdx = _messages.indexWhere((m) => m.id == messageId);
      if (curIdx != -1) {
        _messages[curIdx] = _messages[curIdx].copyWith(
            routedAgent: result.agent.key,
            supportModeLabel: result.supportModeLabel,
            suggestedActions: result.suggestedActions);
      }
      await _refreshQuickPrompts();
      _persist(convId: convIdAtSend);
      _scheduleScrollToBottom(animated: false);
      if (_ttsEnabled && mounted && _currentConvId == convIdAtSend) {
        await OpenAiTtsService.instance.speak(result.reply,
            moodLabel: _currentMoodLabel, messageId: messageId, surface: TtsSurface.chat);
      }
      if (mounted && _currentConvId == convIdAtSend) {
        await _handleMoodFromConversation(userText: userMsg.text, botText: result.reply);
      }
    } catch (e) {
      if (mounted && _currentConvId == convIdAtSend) {
        final ci = _messages.indexWhere((m) => m.id == messageId);
        if (ci != -1) {
          _messages[ci] = _messages[ci].copyWith(
              text: '${_messages[ci].text}\n\n⚠️ Retry failed: $e',
              supportModeLabel: 'Retry issue');
          setState(() {});
          _persist(convId: convIdAtSend);
        }
      }
    } finally {
      if (mounted && _currentConvId == convIdAtSend) {
        setState(() { _isSending = false; _isTyping = false; });
      }
    }
  }

  // ---------- UI helpers ----------

  String _prettyTime(DateTime dt) {
    final now = DateTime.now();
    final sameDay = dt.year == now.year && dt.month == now.month && dt.day == now.day;
    if (sameDay) return "Today ${TimeOfDay.fromDateTime(dt).format(context)}";
    return DateFormat('yyyy-MM-dd').format(dt);
  }

  String _formatMsgTimestamp(DateTime dt) => DateFormat('EEE, MMM d • HH:mm').format(dt);

  String _stripLeadingEmoji(String s) {
    final regex = RegExp(
      r'^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1F1E6}-\u{1F1FF}]+[\s\-:]*',
      unicode: true,
    );
    return s.replaceFirst(regex, '');
  }

  Widget _avatar({required bool isUser}) {
    if (isUser) {
      final userPhoto = FirebaseAuth.instance.currentUser?.photoURL;
      if (userPhoto != null && userPhoto.isNotEmpty) {
        return FadeAvatar(child: CircleAvatar(radius: 16, backgroundImage: NetworkImage(userPhoto)));
      }
      return const FadeAvatar(child: CircleAvatar(radius: 16, child: Icon(Icons.person, size: 18)));
    }
    if (kBotLogoAsset != null) {
      return FadeAvatar(
        child: Container(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            boxShadow: [BoxShadow(color: Colors.blueAccent.withValues(alpha: 0.45), blurRadius: 12, spreadRadius: 2)],
          ),
          child: CircleAvatar(radius: 16, backgroundImage: AssetImage(kBotLogoAsset!)),
        ),
      );
    }
    return const FadeAvatar(child: CircleAvatar(radius: 16, child: Icon(Icons.smart_toy, size: 18)));
  }

  Future<void> _showMessageActions(ChatMessage m) async {
    final isAssistant = m.role == 'assistant';
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.copy),
              title: const Text('Copy'),
              onTap: () {
                Clipboard.setData(ClipboardData(text: m.text));
                Navigator.pop(ctx);
                ScaffoldMessenger.of(context)
                    .showSnackBar(const SnackBar(content: Text('Copied')));
              },
            ),
            if (isAssistant)
              ListTile(
                leading: const Icon(Icons.refresh),
                title: const Text('Regenerate reply'),
                onTap: () { Navigator.pop(ctx); _retryAssistantMessage(m.id); },
              ),
            ListTile(
              leading: const Icon(Icons.delete_outline),
              title: const Text('Delete message'),
              onTap: () {
                setState(() => _messages.removeWhere((x) => x.id == m.id));
                _persist();
                Navigator.pop(ctx);
              },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleAgentAction(AgentAction action, ChatMessage message) async {
    if (action.routeName != null && action.routeName!.isNotEmpty) {
      await Navigator.of(context).pushNamed(action.routeName!);
      return;
    }
    final payload = message.text.trim().isEmpty
        ? (message.supportModeLabel ?? 'MindCore AI note')
        : message.text.trim();
    await Clipboard.setData(ClipboardData(text: payload));
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text('${action.label} copied')));
  }

  Widget _buildActionChips(ChatMessage m, Color color) {
    if (m.suggestedActions.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: m.suggestedActions.take(2).map((action) {
          return ActionChip(
            label: Text(action.label),
            avatar: Icon(
                action.routeName != null ? Icons.arrow_forward_rounded : Icons.copy_rounded,
                size: 16),
            onPressed: () => _handleAgentAction(action, m),
            side: BorderSide(color: color.withValues(alpha: 0.20)),
          );
        }).toList(),
      ),
    );
  }

  Widget _messageItem(ChatMessage m) {
    final isUser = m.role == 'user';
    final theme  = Theme.of(context);
    final bg = isUser ? theme.colorScheme.primaryContainer : theme.colorScheme.surface;
    final fg = isUser ? theme.colorScheme.onPrimaryContainer : theme.colorScheme.onSurface;
    final ts = m.timestamp ?? DateTime.now();
    final maxBubbleWidth = MediaQuery.of(context).size.width * 0.82;

    final bubble = ConstrainedBox(
      constraints: BoxConstraints(maxWidth: maxBubbleWidth),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onLongPress: () => _showMessageActions(m),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(16),
            boxShadow: isUser
                ? [BoxShadow(color: theme.colorScheme.primary.withValues(alpha: 0.25), blurRadius: 8, offset: const Offset(0, 3))]
                : const [BoxShadow(blurRadius: 6, color: Color(0x14000000), offset: Offset(0, 2))],
          ),
          child: Column(
            crossAxisAlignment: isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
            children: [
              if (!isUser && (m.supportModeLabel ?? '').isNotEmpty) ...[
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                      color: theme.colorScheme.primary.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(999)),
                  child: Text(m.supportModeLabel!,
                      style: theme.textTheme.labelMedium?.copyWith(
                          color: theme.colorScheme.primary, fontWeight: FontWeight.w700)),
                ),
                const SizedBox(height: 8),
              ],
              Text(m.text, style: TextStyle(color: fg, height: 1.32)),
              if (!isUser) _buildActionChips(m, theme.colorScheme.primary),
              const SizedBox(height: 6),
              Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Text(_formatMsgTimestamp(ts),
                    style: theme.textTheme.bodySmall?.copyWith(
                        color: isUser
                            ? Colors.black87
                            : theme.colorScheme.onSurface.withValues(alpha: 0.6))),
              ),
              if (m.role == 'assistant') ...[
                const SizedBox(height: 6),
                Row(mainAxisSize: MainAxisSize.min, children: [
                  IconButton(
                    icon: Icon(_ttsEnabled ? Icons.volume_up : Icons.volume_off),
                    tooltip: _ttsEnabled ? 'Mute voice' : 'Read replies aloud',
                    onPressed: () async {
                      final newValue = !_ttsEnabled;
                      setState(() => _ttsEnabled = newValue);
                      await OpenAiTtsService.instance.setSurfaceEnabled(TtsSurface.chat, newValue);
                      if (!newValue) await _stopSpeech(resetState: true);
                    },
                  ),
                ]),
              ],
            ],
          ),
        ),
      ),
    );

    final row = Row(
      mainAxisAlignment: isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: isUser
          ? [Flexible(child: bubble), const SizedBox(width: 8), _avatar(isUser: true)]
          : [_avatar(isUser: false), const SizedBox(width: 8), Flexible(child: bubble)],
    );

    return Padding(
        padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 10), child: row);
  }

  Widget _buildEmptyState() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.74),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface.withValues(alpha: 0.92),
            borderRadius: BorderRadius.circular(16),
            boxShadow: const [BoxShadow(blurRadius: 6, color: Color(0x14000000), offset: Offset(0, 2))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Your guide is ready whenever you are.',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text('Start typing to begin your check-in.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.72))),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 10),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
        decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(16)),
        child: const Text('…typing'),
      ),
    );
  }

  Future<void> _openSwitcher() async {
    if (_isSending) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please wait for the reply to finish…')));
      return;
    }
    _convs = await ChatPersistence.listConversations();
    if (!mounted) return;
    final selected = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: ListView(
          children: [
            ListTile(
                leading: const Icon(Icons.add_circle_outline),
                title: const Text('New chat'),
                onTap: () => Navigator.pop(ctx, '__new__')),
            const Divider(height: 0),
            ..._convs.map((c) => ListTile(
                leading: Icon(c.id == _currentConvId ? Icons.chat_bubble : Icons.chat_bubble_outline),
                title: Text(c.title),
                subtitle: Text(_prettyTime(c.updatedAt)),
                onTap: () => Navigator.pop(ctx, c.id))),
          ],
        ),
      ),
    );
    if (selected == null) return;
    if (selected == '__new__') return _newConversation();
    return _switchConversation(selected);
  }

  @override
  Widget build(BuildContext context) {
    final rawTitle = _convs
        .firstWhere((c) => c.id == _currentConvId,
            orElse: () => ConversationMeta(id: _currentConvId, title: 'Chat'))
        .title;
    final baseTitle      = _stripLeadingEmoji(rawTitle);
    final decoratedTitle = _currentMoodEmoji == null ? baseTitle : '$baseTitle ${_currentMoodEmoji!}';
    final bottomInset    = MediaQuery.of(context).viewInsets.bottom;
    final safeBottom     = MediaQuery.of(context).viewPadding.bottom;

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppTopBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new),
          tooltip: 'Back',
          onPressed: () {
            final navigator = Navigator.of(context);
            if (navigator.canPop()) {
              navigator.pop();
            } else {
              Navigator.of(context).pushReplacementNamed('/home');
            }
          },
        ),
        title: decoratedTitle,
        actions: [
          const UsageBanner(compact: true),
          const SizedBox(width: 4),
          IconButton(icon: const Icon(Icons.mood), tooltip: 'Log mood', onPressed: _onLogMoodPressed),
          IconButton(
            icon: Icon(_ttsEnabled ? Icons.volume_up : Icons.volume_off),
            tooltip: _ttsEnabled ? 'Mute voice' : 'Read replies aloud',
            onPressed: () async {
              final newValue = !_ttsEnabled;
              setState(() => _ttsEnabled = newValue);
              await OpenAiTtsService.instance.setSurfaceEnabled(TtsSurface.chat, newValue);
              if (!newValue) await _stopSpeech(resetState: true);
            },
          ),
          IconButton(icon: const Icon(Icons.folder_open), tooltip: 'Switch chat', onPressed: _openSwitcher),
          PopupMenuButton<String>(
            onSelected: (v) {
              if (v == 'rename') _renameConversation();
              if (v == 'clear')  _clearHistory();
              if (v == 'delete') _deleteConversation();
            },
            itemBuilder: (ctx) => const [
              PopupMenuItem(value: 'rename', child: Text('Rename chat')),
              PopupMenuItem(value: 'clear',  child: Text('Clear messages')),
              PopupMenuItem(value: 'delete', child: Text('Delete chat')),
            ],
          ),
        ],
      ),
      body: GradientBackground(
        child: AnimatedBackdrop(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 0),
            child: Column(
              children: [
                Expanded(
                  child: GlassCard(
                    child: Column(
                      children: [
                        // ── Disclaimer banner ───────────────────────────
                        const DisclaimerBanner(),

                        if (_therapistMode.enabled)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                            child: Align(
                                alignment: Alignment.centerLeft,
                                child: _buildTherapistModeChip()),
                          ),

                        Expanded(
                          child: ListView.builder(
                            controller: _scroll,
                            keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                            padding: const EdgeInsets.fromLTRB(0, 8, 0, 8),
                            itemCount: (_messages.isEmpty ? 1 : _messages.length) + (_isTyping ? 1 : 0),
                            itemBuilder: (context, index) {
                              if (_messages.isEmpty && index == 0) return _buildEmptyState();
                              final adjustedIndex = _messages.isEmpty ? index - 1 : index;
                              if (_isTyping && adjustedIndex == _messages.length) {
                                return _buildTypingIndicator();
                              }
                              return _messageItem(_messages[adjustedIndex]);
                            },
                          ),
                        ),

                        _buildMoodSuggestionBar(),

                        if (_showResetNudge)
                          Padding(
                            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
                            child: GlassCard(
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Row(
                                  children: [
                                    const Icon(Icons.spa_outlined),
                                    const SizedBox(width: 10),
                                    const Expanded(
                                        child: Text('Want a quick reset? 90 seconds can help.',
                                            style: TextStyle(fontWeight: FontWeight.w600))),
                                    TextButton(
                                        onPressed: () async {
                                          setState(() => _showResetNudge = false);
                                          await _stopSpeech(resetState: true);
                                          if (!mounted) return;
                                          Navigator.of(context).pushNamed('/reset');
                                        },
                                        child: const Text('Start')),
                                    IconButton(
                                        onPressed: () => setState(() => _showResetNudge = false),
                                        icon: const Icon(Icons.close, size: 18)),
                                  ],
                                ),
                              ),
                            ),
                          ),

                        SafeArea(
                          top: false,
                          child: Padding(
                            padding: EdgeInsets.fromLTRB(
                                10,
                                6,
                                10,
                                bottomInset > 0
                                    ? 10
                                    : (10 + safeBottom.clamp(0, 12))),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Expanded(
                                  child: TextField(
                                    controller: _controller,
                                    focusNode: _composerFocus,
                                    textInputAction: TextInputAction.send,
                                    onSubmitted: (_) => _send(),
                                    onTap: () => _scheduleScrollToBottom(animated: false),
                                    minLines: 1,
                                    maxLines: 3,
                                    decoration: InputDecoration(
                                      hintText: 'Type a message…',
                                      filled: true,
                                      isDense: true,
                                      contentPadding: const EdgeInsets.symmetric(
                                          horizontal: 18, vertical: 16),
                                      border: OutlineInputBorder(
                                          borderRadius: BorderRadius.circular(18),
                                          borderSide: BorderSide.none),
                                      fillColor: Theme.of(context).colorScheme.surface,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Padding(
                                  padding: const EdgeInsets.only(bottom: 2),
                                  child: IconButton(
                                      onPressed: _isSending ? null : _send,
                                      icon: const Icon(Icons.send_rounded),
                                      tooltip: 'Send'),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class FadeAvatar extends StatefulWidget {
  final Widget child;
  const FadeAvatar({super.key, required this.child});
  @override
  State<FadeAvatar> createState() => _FadeAvatarState();
}

class _FadeAvatarState extends State<FadeAvatar> with SingleTickerProviderStateMixin {
  late AnimationController _c;
  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 350))..forward();
  }
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => FadeTransition(opacity: _c, child: widget.child);
}

bool _shouldShowResetNudge(String text) {
  final t = text.toLowerCase();
  const cues = [
    'overwhelmed', 'cant cope', 'panic', 'panicking', 'anxious', 'anxiety',
    'stressed', 'stress', 'too much', 'i cant breathe', 'spiral', 'overthinking',
    'my chest', 'heart racing', 'i feel trapped',
  ];
  return cues.any(t.contains);
}
