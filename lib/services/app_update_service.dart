// lib/services/app_update_service.dart
//
// In-app update prompts via Google Play Core API.
// Checks for updates on app start and shows flexible or immediate prompts.

import 'package:flutter/material.dart';
import 'package:in_app_update/in_app_update.dart';

class AppUpdateService {
  AppUpdateService._();

  /// Check for updates and prompt the user if one is available.
  /// Call this from the home screen's initState.
  ///
  /// - Flexible update: shows a banner, user can dismiss and update later.
  ///   Use for feature releases.
  /// - Immediate update: blocks the app until updated.
  ///   Use for critical security fixes (set [forceUpdate] = true).
  static Future<void> checkForUpdate({bool forceUpdate = false}) async {
    try {
      final info = await InAppUpdate.checkForUpdate();

      if (!info.updateAvailability.isUpdateAvailable) return;

      if (forceUpdate || info.immediateUpdateAllowed) {
        // Critical update — block until installed
        if (forceUpdate) {
          await InAppUpdate.performImmediateUpdate();
          return;
        }
      }

      if (info.flexibleUpdateAllowed) {
        // Normal update — download in background, prompt to install
        await InAppUpdate.startFlexibleUpdate();
        // Once downloaded, prompt user to restart
        await InAppUpdate.completeFlexibleUpdate();
      }
    } catch (e) {
      // Silently fail — update checks should never crash the app.
      // Common failures: not installed via Play Store (debug builds),
      // no network, Play Services unavailable.
      debugPrint('AppUpdateService: $e');
    }
  }
}

extension on UpdateAvailability {
  bool get isUpdateAvailable =>
      this == UpdateAvailability.updateAvailable;
}
