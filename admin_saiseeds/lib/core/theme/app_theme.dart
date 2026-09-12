import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'app_colors.dart';
import 'app_spacing.dart';
import 'app_typography.dart';

class AppTheme {
  AppTheme._();

  static ThemeData get light {
    return ThemeData(
      useMaterial3: true,
      fontFamily: GoogleFonts.inter().fontFamily,
      scaffoldBackgroundColor: AppColors.BACKGROUND,
      hoverColor: AppColors.TRANSPARENT,
      splashColor: AppColors.TRANSPARENT,
      highlightColor: AppColors.TRANSPARENT,
      colorScheme: const ColorScheme(
        brightness: Brightness.light,
        primary: AppColors.PRIMARY,
        onPrimary: AppColors.TEXT_ON_PRIMARY,
        secondary: AppColors.PRIMARY_DARK,
        onSecondary: AppColors.TEXT_ON_PRIMARY,
        error: AppColors.ERROR,
        onError: AppColors.TEXT_ON_PRIMARY,
        surface: AppColors.SURFACE,
        onSurface: AppColors.TEXT_PRIMARY,
      ),
      textTheme: TextTheme(
        displayLarge: AppTypography.headingLarge,
        headlineLarge: AppTypography.headingLarge,
        headlineMedium: AppTypography.headingMedium,
        headlineSmall: AppTypography.headingSmall,
        titleLarge: AppTypography.titleMedium,
        bodyLarge: AppTypography.bodyLarge,
        bodyMedium: AppTypography.bodyMedium,
        bodySmall: AppTypography.bodySmall,
        labelLarge: AppTypography.label,
        labelSmall: AppTypography.caption,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.SURFACE,
        foregroundColor: AppColors.TEXT_PRIMARY,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: AppTypography.headingSmall,
      ),
      cardTheme: CardThemeData(
        color: AppColors.SURFACE,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.sm),
          side: const BorderSide(color: AppColors.BORDER),
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.PRIMARY,
          foregroundColor: AppColors.TEXT_ON_PRIMARY,
          disabledBackgroundColor: AppColors.TEXT_DISABLED,
          minimumSize: const Size(120, 44),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.sm,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.xs),
          ),
          elevation: 0,
          shadowColor: Colors.transparent,
          textStyle: AppTypography.button,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.PRIMARY,
          minimumSize: const Size(120, 44),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.sm,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppSpacing.xs),
          ),
          side: const BorderSide(color: AppColors.BORDER),
          textStyle: AppTypography.button,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.PRIMARY,
          textStyle: AppTypography.button,
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.SURFACE,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          borderSide: const BorderSide(color: AppColors.BORDER),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          borderSide: const BorderSide(color: AppColors.BORDER),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          borderSide: const BorderSide(
            color: AppColors.BORDER_FOCUSED,
            width: 1.5,
          ),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          borderSide: const BorderSide(color: AppColors.ERROR),
        ),
        focusedErrorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          borderSide: const BorderSide(color: AppColors.ERROR, width: 1.5),
        ),
        hintStyle: AppTypography.bodyMedium,
        labelStyle: AppTypography.label,
        errorStyle: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.DIVIDER,
        thickness: 1,
        space: 0,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.SURFACE,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.sm),
        ),
      ),
      popupMenuTheme: PopupMenuThemeData(
        color: AppColors.SURFACE,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs),
          side: const BorderSide(color: AppColors.BORDER),
        ),
      ),
      snackBarTheme: const SnackBarThemeData(
        backgroundColor: AppColors.TEXT_PRIMARY,
        elevation: 0,
        behavior: SnackBarBehavior.floating,
      ),
      scrollbarTheme: ScrollbarThemeData(
        thumbColor: WidgetStateProperty.all(AppColors.DIVIDER),
        radius: const Radius.circular(AppSpacing.xs),
      ),
      checkboxTheme: CheckboxThemeData(
        fillColor: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) return AppColors.PRIMARY;
          return Colors.transparent;
        }),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppSpacing.xs / 2),
        ),
        side: const BorderSide(color: AppColors.BORDER, width: 1.5),
      ),
    );
  }
}
