// lib/pages/onboarding_screen.dart
//
// First-launch onboarding — 9 stages:
//  0  Orb reveal + tagline
//  1  Mission statement
//  2  Feature carousel
//  3  About you (name, current feeling, what brings you here)
//  4  Support preferences (support style, openness, initial note)
//  5  Voice selection
//  6  Disclaimer
//  7  Privacy & transparency
//  8  Notification permission

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:mindcore_ai/widgets/animated_backdrop.dart';
import 'package:mindcore_ai/widgets/mood_orb.dart';
import 'package:mindcore_ai/widgets/glass_card.dart';
import 'package:mindcore_ai/widgets/app_gradients.dart';
import 'package:mindcore_ai/services/settings_service.dart';
import 'package:mindcore_ai/services/persona_service.dart';
import 'package:mindcore_ai/services/live_voice_preferences.dart';
import 'package:mindcore_ai/services/user_profile_service.dart';

enum _Stage {
  orb, mission, features,
  aboutYou, supportPrefs,
  voiceSelect, disclaimer, privacy, notifications,
}
