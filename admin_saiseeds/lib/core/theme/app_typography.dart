import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../constants/font_sizes.dart';
import 'app_colors.dart';

class AppTypography {
  AppTypography._();

  static TextStyle get display => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_28,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_PRIMARY,
    letterSpacing: -0.8,
    height: 1.1,
  );

  static TextStyle get overline => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_10,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_SECONDARY,
    letterSpacing: 0.8,
  );

  static TextStyle get headingLarge => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_32,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get headingMedium => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_24,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get headingSmall => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_20,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get titleMedium => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_18,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get bodyLarge => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_16,
    fontWeight: FontWeight.w400,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get bodyMedium => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_14,
    fontWeight: FontWeight.w400,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get bodySmall => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_12,
    fontWeight: FontWeight.w400,
    color: AppColors.TEXT_SECONDARY,
  );

  static TextStyle get label => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_14,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_PRIMARY,
    letterSpacing: 0.1,
  );

  static TextStyle get labelStrong => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_12,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_PRIMARY,
    letterSpacing: 0.6,
  );

  static TextStyle get otpDigit => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_24,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_PRIMARY,
    letterSpacing: 0.4,
  );

  static TextStyle get caption => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_12,
    fontWeight: FontWeight.w400,
    color: AppColors.TEXT_SECONDARY,
  );

  static TextStyle get button => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_14,
    fontWeight: FontWeight.w600,
    letterSpacing: 0.2,
  );

  static TextStyle get tableHeader => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_11,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_ON_PRIMARY,
    letterSpacing: 0.5,
  );

  static TextStyle get tableCell => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_13,
    fontWeight: FontWeight.w500,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get tableCellStrong => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_13,
    fontWeight: FontWeight.w700,
    color: AppColors.TEXT_PRIMARY,
  );

  static TextStyle get labelSmall => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_11,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_SECONDARY,
  );

  static TextStyle get labelMedium => GoogleFonts.inter(
    fontSize: AppFontSizes.FONT_13,
    fontWeight: FontWeight.w600,
    color: AppColors.TEXT_PRIMARY,
  );
}
