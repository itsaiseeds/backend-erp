import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/feedback/app_badge.dart';

class ProfilePermissionRow extends StatelessWidget {
  final String label;
  final String description;
  final IconData icon;
  final bool isGranted;

  const ProfilePermissionRow({
    super.key,
    required this.label,
    required this.description,
    required this.icon,
    required this.isGranted,
  });

  @override
  Widget build(BuildContext context) {
    final Color accent = isGranted
        ? AppColors.PRIMARY
        : AppColors.TEXT_DISABLED;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.smd),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: AppSizes.profilePermissionIconTile,
            height: AppSizes.profilePermissionIconTile,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: isGranted
                  ? AppColors.PRIMARY_SURFACE
                  : AppColors.SURFACE_VARIANT,
              borderRadius: const BorderRadius.all(
                Radius.circular(AppRadius.sm),
              ),
            ),
            child: Icon(icon, size: AppSizes.iconMd, color: accent),
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.labelMedium.copyWith(
                    color: AppColors.TEXT_PRIMARY,
                  ),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  description,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          AppBadge(
            label: isGranted
                ? AppStrings.PROFILE_PERMISSION_GRANTED
                : AppStrings.PROFILE_PERMISSION_RESTRICTED,
            variant: isGranted
                ? AppBadgeVariant.success
                : AppBadgeVariant.neutral,
          ),
        ],
      ),
    );
  }
}
