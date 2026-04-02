import 'package:flutter/material.dart';

/// Central visual system for MindCore AI.
/// Dark-first, neon-accented, futuristic wellness palette.
class AppColors {
  // ── Night backgrounds ──────────────────────────────────────────
  static const Color nightDeep   = Color(0xFF060D18);
  static const Color nightTop    = Color(0xFF0A1628);
  static const Color nightMid    = Color(0xFF0C1C32);
  static const Color nightBottom = Color(0xFF080F1C);

  // ── Light (mist) backgrounds ───────────────────────────────────
  static const Color mistTop    = Color(0xFFB8B4F0);
  static const Color mistMid    = Color(0xFFDDF7F0);
  static const Color mistBottom = Color(0xFFE9F3FF);

  // ── Primary neon accents ───────────────────────────────────────
  static const Color primary      = Color(0xFF4D7CFF);
  static const Color primaryLight = Color(0xFF74C3FF);
  static const Color primaryGlow  = Color(0xFF3B6EF0);

  // ── Teal / mint ────────────────────────────────────────────────
  static const Color mint         = Color(0xFF89E0CF);
  static const Color mintDeep     = Color(0xFF32D0BE);
  static const Color mintGlow     = Color(0xFF25BCA9);

  // ── Violet accent ──────────────────────────────────────────────
  static const Color violet       = Color(0xFF9B7FFF);
  static const Color violetDeep   = Color(0xFF7B5FE0);
  static const Color lavender     = Color(0xFFB8B4F0);

  // ── Glow colours (with opacity baked in) ──────────────────────
  static const Color glowBlue    = Color(0x664D7CFF);
  static const Color glowMint    = Color(0x5532D0BE);
  static const Color glowViolet  = Color(0x449B7FFF);

  // ── Glass surfaces ─────────────────────────────────────────────
  static const Color glassLight  = Color(0xF2FFFFFF);
  static const Color glassBorder = Color(0x66FFFFFF);
}

class AppGradients {
  // ── Full-screen body gradient ──────────────────────────────────
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

  // ── AppBar gradient ────────────────────────────────────────────
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

  // ── Hero glow overlay inside glass cards ──────────────────────
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

  // ── Button gradients ───────────────────────────────────────────
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

  static const LinearGradient violetButton = LinearGradient(
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
    colors: [AppColors.violetDeep, AppColors.violet],
  );

  static const LinearGradient glassFill = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xEFFFFFFF), Color(0xCFFFFFFF)],
  );
}
