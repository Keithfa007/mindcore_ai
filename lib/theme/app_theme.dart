import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTokens {
  static const Color primaryBlue = Color(0xFF4D7CFF);
  static const Color primaryBlueLight = Color(0xFF74C3FF);
  static const Color mint = Color(0xFF89E0CF);
  static const Color mintDeep = Color(0xFF32D0BE);
  static const Color outline = Color(0x22FFFFFF);
  static const Color divider = Color(0x14FFFFFF);

  static const double rLg = 20;
  static const double rMd = 16;
  static const double rSm = 11;
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
      surface: const Color(0xFFF8FBFF),
    );

    final textTheme = GoogleFonts.manropeTextTheme().copyWith(
      headlineMedium: GoogleFonts.manrope(
        fontSize: 20,
        fontWeight: FontWeight.w800,
        letterSpacing: -1.0,
        color: const Color(0xFF0E1320),
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
      labelSmall: GoogleFonts.manrope(
        fontSize: 10.25,
        fontWeight: FontWeight.w700,
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
        backgroundColor: Colors.transparent,
        foregroundColor: scheme.onSurface,
        titleTextStyle: textTheme.titleLarge,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.80),
        hintStyle: textTheme.bodyLarge?.copyWith(
          color: const Color(0xFF667085),
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.70)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.74)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: const BorderSide(color: AppTokens.primaryBlue, width: 1.8),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 15, vertical: 12),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          foregroundColor: Colors.white,
          backgroundColor: AppTokens.primaryBlue,
          minimumSize: const Size.fromHeight(46),
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
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
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
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: Colors.white.withValues(alpha: 0.76),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.72)),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      ),
      dividerColor: const Color(0x14FFFFFF),
    );
  }

  static ThemeData dark() {
    final base = ThemeData(
      brightness: Brightness.dark,
      useMaterial3: true,
    );
    final textTheme = GoogleFonts.manropeTextTheme(base.textTheme);
    return base.copyWith(
      colorScheme: base.colorScheme.copyWith(
        primary: AppTokens.primaryBlue,
        secondary: AppTokens.mint,
        surface: const Color(0xFF101826),
      ),
      textTheme: textTheme,
      scaffoldBackgroundColor: Colors.transparent,
      splashFactory: InkSparkle.splashFactory,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.06),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.08)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppTokens.rLg),
          borderSide: const BorderSide(color: AppTokens.primaryBlue, width: 1.7),
        ),
      ),
    );
  }
}
