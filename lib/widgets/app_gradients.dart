import 'package:flutter/material.dart';

/// Central visual system for the app.
class AppColors {
  static const Color mistTop = Color(0xFFB8B4F0);
  static const Color mistMid = Color(0xFFDDF7F0);
  static const Color mistBottom = Color(0xFFE9F3FF);

  static const Color nightTop = Color(0xFF0B1220);
  static const Color nightMid = Color(0xFF0B1827);
  static const Color nightBottom = Color(0xFF09101A);

  static const Color primary = Color(0xFF4D7CFF);
  static const Color primaryLight = Color(0xFF74C3FF);
  static const Color mint = Color(0xFF89E0CF);
  static const Color mintDeep = Color(0xFF32D0BE);
  static const Color lavender = Color(0xFFB8B4F0);

  static const Color glassLight = Color(0xF2FFFFFF);
  static const Color glassBorder = Color(0x66FFFFFF);
  static const Color glowBlue = Color(0x664D7CFF);
  static const Color glowMint = Color(0x5532D0BE);
}

class AppGradients {
  static Gradient body(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return isDark
        ? const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppColors.nightTop,
              AppColors.nightMid,
              AppColors.nightBottom,
            ],
            stops: [0.0, 0.55, 1.0],
          )
        : const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              AppColors.mistTop,
              AppColors.mistMid,
              AppColors.mistBottom,
            ],
            stops: [0.0, 0.52, 1.0],
          );
  }

  static Gradient appBar(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return isDark
        ? const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF10192B), Color(0xFF0D1422)],
          )
        : const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFFCAC6F7), Color(0xFFBBB8F2)],
          );
  }

  static Gradient heroGlow(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return isDark
        ? const RadialGradient(
            center: Alignment(-0.65, -0.9),
            radius: 1.35,
            colors: [Color(0x3332D0BE), Color(0x224D7CFF), Colors.transparent],
            stops: [0.0, 0.38, 1.0],
          )
        : const RadialGradient(
            center: Alignment(-0.65, -0.9),
            radius: 1.35,
            colors: [Color(0x66FFFFFF), Color(0x334D7CFF), Colors.transparent],
            stops: [0.0, 0.32, 1.0],
          );
  }

  static Color bodyLightColor(BuildContext context) {
    final g = body(context);
    if (g is LinearGradient && g.colors.isNotEmpty) return g.colors.last;
    return Theme.of(context).colorScheme.surface;
  }

  static Color bodyDarkColor(BuildContext context) {
    final g = body(context);
    if (g is LinearGradient && g.colors.isNotEmpty) return g.colors.first;
    return Theme.of(context).colorScheme.surfaceContainerHighest;
  }

  static const LinearGradient primaryButton = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [AppColors.primary, AppColors.primaryLight],
  );

  static const LinearGradient mintButton = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [AppColors.mintDeep, AppColors.mint],
  );

  static const LinearGradient glassFill = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xEFFFFFFF), Color(0xCFFFFFFF)],
  );
}
