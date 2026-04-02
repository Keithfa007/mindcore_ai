import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import '../widgets/app_gradients.dart';

class AppTokens {
  // ── Colours ────────────────────────────────────────────────────
  static const Color primaryBlue      = Color(0xFF4D7CFF);
  static const Color primaryBlueLight = Color(0xFF74C3FF);
  static const Color mint             = Color(0xFF89E0CF);
  static const Color mintDeep         = Color(0xFF32D0BE);
  static const Color violet           = Color(0xFF9B7FFF);
  static const Color outline          = Color(0x22FFFFFF);
  static const Color divider          = Color(0x14FFFFFF);

  // ── Radius ─────────────────────────────────────────────────────
  static const double rLg = 20;
  static const double rMd = 16;
  static const double rSm = 11;
  static const double rXl = 28;

  // ── Elevation / shadow ─────────────────────────────────────────
  static const double cardElevation = 0;

  static const EdgeInsets screenPad =
      EdgeInsets.symmetric(horizontal: 18, vertical: 12);
}

class AppTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(
      seedColor: AppTokens.primaryBlue,
      brightness: Brightness.light,
      primary: AppTokens.primaryBlue,
      secondary: AppTokens.mint,
      tertiary: AppTokens.violet,
      surface: const Color(0xFFF8FBFF),
    );

    final textTheme = GoogleFonts.manropeTextTheme().copyWith(
      displaySmall: GoogleFonts.manrope(
        fontSize: 28,
        fontWeight: FontWeight.w900,
        letterSpacing: -1.2,
        color: const Color(0xFF0E1320),
      ),
      headlineMedium: GoogleFonts.manrope(
        fontSize: 22,
        fontWeight: FontWeight.w800,
        letterSpacing: -1.0,
        color: const Color(0xFF0E1320),
      ),
      headlineSmall: GoogleFonts.manrope(
        fontSize: 19,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.7,
        color: const Color(0xFF111827),
      ),
      titleLarge: GoogleFonts.manrope(
        fontSize: 18.5,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.6,
        color: const Color(0xFF111827),
      ),
      titleMedium: GoogleFonts.manrope(
        fontSize: 15,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.3,
        color: const Color(0xFF111827),
      ),
      titleSmall: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
        color: const Color(0xFF1F2937),
      ),
      bodyLarge: GoogleFonts.manrope(
        fontSize: 14.5,
        height: 1.32,
        color: const Color(0xFF374151),
      ),
      bodyMedium: GoogleFonts.manrope(
        fontSize: 13.5,
        height: 1.32,
        color: const Color(0xFF475467),
      ),
      bodySmall: GoogleFonts.manrope(
        fontSize: 12,
        height: 1.26,
        color: const Color(0xFF667085),
      ),
      labelLarge: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.1,
      ),
      labelSmall: GoogleFonts.manrope(
        fontSize: 10.25,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.3,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      textTheme: textTheme,
      scaffoldBackgroundColor: Colors.transparent,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: scheme.onSurface,
        systemOverlayStyle: SystemUiOverlayStyle.dark,
        titleTextStyle: textTheme.titleLarge,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.80),
        hintStyle:
            textTheme.bodyLarge?.copyWith(color: const Color(0xFF667085)),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.70)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.74)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: const BorderSide(
              color: AppTokens.primaryBlue, width: 1.8),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          foregroundColor: Colors.white,
          backgroundColor: AppTokens.primaryBlue,
          minimumSize: const Size.fromHeight(48),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTokens.rLg),
          ),
          textStyle: textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          foregroundColor: Colors.white,
          elevation: 0,
          padding:
              const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTokens.rLg),
          ),
          textStyle: textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: const Color(0xFF111827),
          side: BorderSide(color: Colors.white.withValues(alpha: 0.75)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppTokens.rLg),
          ),
          padding:
              const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white.withValues(alpha: 0.76),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.72)),
        padding:
            const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      ),
      dividerColor: const Color(0x14FFFFFF),
    );
  }

  static ThemeData dark() {
    final base = ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
    );

    final textTheme = GoogleFonts.manropeTextTheme(base.textTheme).copyWith(
      displaySmall: GoogleFonts.manrope(
        fontSize: 28,
        fontWeight: FontWeight.w900,
        letterSpacing: -1.2,
        color: Colors.white,
      ),
      headlineMedium: GoogleFonts.manrope(
        fontSize: 22,
        fontWeight: FontWeight.w800,
        letterSpacing: -1.0,
        color: Colors.white,
      ),
      headlineSmall: GoogleFonts.manrope(
        fontSize: 19,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.7,
        color: Colors.white,
      ),
      titleLarge: GoogleFonts.manrope(
        fontSize: 18.5,
        fontWeight: FontWeight.w800,
        letterSpacing: -0.6,
        color: Colors.white,
      ),
      titleMedium: GoogleFonts.manrope(
        fontSize: 15,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.3,
        color: Colors.white,
      ),
      titleSmall: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.2,
        color: const Color(0xFFE2E8F0),
      ),
      bodyLarge: GoogleFonts.manrope(
        fontSize: 14.5,
        height: 1.32,
        color: const Color(0xFFCBD5E1),
      ),
      bodyMedium: GoogleFonts.manrope(
        fontSize: 13.5,
        height: 1.32,
        color: const Color(0xFF94A3B8),
      ),
      bodySmall: GoogleFonts.manrope(
        fontSize: 12,
        height: 1.26,
        color: const Color(0xFF64748B),
      ),
      labelLarge: GoogleFonts.manrope(
        fontSize: 13,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.1,
        color: const Color(0xFFCBD5E1),
      ),
      labelSmall: GoogleFonts.manrope(
        fontSize: 10.25,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.3,
        color: const Color(0xFF94A3B8),
      ),
    );

    return base.copyWith(
      colorScheme: ColorScheme.dark(
        primary: AppTokens.primaryBlue,
        primaryContainer: const Color(0xFF1A2B4A),
        secondary: AppTokens.mint,
        secondaryContainer: const Color(0xFF0D2A26),
        tertiary: AppTokens.violet,
        tertiaryContainer: const Color(0xFF1E1540),
        surface: const Color(0xFF0C1622),
        surfaceContainerHighest: const Color(0xFF141F30),
        surfaceContainerHigh: const Color(0xFF111A28),
        surfaceContainer: const Color(0xFF0E1826),
        onSurface: Colors.white,
        onSurfaceVariant: const Color(0xFF94A3B8),
        outline: const Color(0xFF1E2D42),
        outlineVariant: const Color(0xFF162030),
        error: const Color(0xFFFF6B6B),
        onError: Colors.white,
      ),
      textTheme: textTheme,
      scaffoldBackgroundColor: Colors.transparent,
      splashFactory: InkSparkle.splashFactory,
      appBarTheme: AppBarTheme(
        centerTitle: true,
        elevation: 0,
        scrolledUnderElevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: Colors.white,
        systemOverlayStyle: SystemUiOverlayStyle.light,
        titleTextStyle: textTheme.titleLarge,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide:
              BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: const BorderSide(
              color: AppTokens.primaryBlue, width: 1.7),
        ),
        hintStyle: textTheme.bodyMedium,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white.withValues(alpha: 0.06),
        selectedColor: AppTokens.primaryBlue.withValues(alpha: 0.25),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.10)),
        labelStyle: textTheme.labelSmall,
        padding:
            const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      ),
      dividerColor: Colors.white.withValues(alpha: 0.06),
      dividerTheme: DividerThemeData(
        color: Colors.white.withValues(alpha: 0.06),
        thickness: 1,
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppTokens.primaryBlue;
          }
          return const Color(0xFF475569);
        }),
        trackColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return AppTokens.primaryBlue.withValues(alpha: 0.35);
          }
          return Colors.white.withValues(alpha: 0.08);
        }),
      ),
      sliderTheme: SliderThemeData(
        activeTrackColor: AppTokens.primaryBlue,
        inactiveTrackColor: Colors.white.withValues(alpha: 0.10),
        thumbColor: AppTokens.primaryBlue,
        overlayColor: AppTokens.primaryBlue.withValues(alpha: 0.20),
      ),
    );
  }
}
