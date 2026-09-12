import 'package:flutter/material.dart';
import '../../constants/font_sizes.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

enum AppBadgeVariant { success, warning, error, info, neutral }

class AppBadge extends StatelessWidget {
  final String label;
  final AppBadgeVariant variant;

  const AppBadge({
    super.key,
    required this.label,
    this.variant = AppBadgeVariant.neutral,
  });

  ({Color background, Color foreground}) get _colors {
    switch (variant) {
      case AppBadgeVariant.success:
        return (
          background: AppColors.SUCCESS_LIGHT,
          foreground: AppColors.SUCCESS,
        );
      case AppBadgeVariant.warning:
        return (
          background: AppColors.WARNING_LIGHT,
          foreground: AppColors.WARNING,
        );
      case AppBadgeVariant.error:
        return (background: AppColors.ERROR_LIGHT, foreground: AppColors.ERROR);
      case AppBadgeVariant.info:
        return (background: AppColors.INFO_LIGHT, foreground: AppColors.INFO);
      case AppBadgeVariant.neutral:
        return (
          background: AppColors.SURFACE_VARIANT,
          foreground: AppColors.TEXT_SECONDARY,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = _colors;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: colors.background,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Text(
        label,
        style: AppTypography.caption.copyWith(
          color: colors.foreground,
          fontSize: AppFontSizes.FONT_12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
