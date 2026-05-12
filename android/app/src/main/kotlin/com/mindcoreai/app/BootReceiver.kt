package com.mindcoreai.app

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Catches BOOT_COMPLETED and MY_PACKAGE_REPLACED broadcasts.
 *
 * Android clears all AlarmManager alarms on device restart, which means
 * flutter_local_notifications scheduled alarms are wiped. This receiver
 * stores a flag in SharedPreferences so that the next time Flutter runs
 * NotificationService.init() it knows to force-reschedule everything.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED ||
            intent.action == Intent.ACTION_MY_PACKAGE_REPLACED) {
            // Flutter's SharedPreferences plugin stores keys with "flutter." prefix
            val prefs = context.getSharedPreferences(
                "FlutterSharedPreferences", Context.MODE_PRIVATE
            )
            prefs.edit()
                .putBoolean("flutter.needs_notification_reschedule", true)
                .apply()
        }
    }
}
