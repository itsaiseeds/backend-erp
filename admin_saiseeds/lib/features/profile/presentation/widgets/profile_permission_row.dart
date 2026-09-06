import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/feedback/app_badge.dart';

class ProfilePermissionRow extends StatelessWidget {
  final String label;
  final bool isGranted;

  const ProfilePermissionRow({
    super.key,
    required this.label,
    required this.isGranted,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: BoxDecoration(
        color: isGranted ? AppColors.SURFACE : AppColors.SURFACE_VARIANT,
        border: Border.fromBorderSide(
          BorderSide(
            color: isGranted ? AppColors.PRIMARY : AppColors.BORDER,
            width: AppSizes.borderThin,
          ),
        ),
        borderRadius: const BorderRadius.all(Radius.circular(AppRadius.md)),
      ),
      child: Row(
        children: [
          Icon(
            isGranted
                ? Icons.check_circle_outline_rounded
                : Icons.remove_circle_outline_rounded,
            size: AppSizes.iconLg,
            color: isGranted ? AppColors.PRIMARY : AppColors.TEXT_DISABLED,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodyMedium.copyWith(
                fontWeight: FontWeight.w500,
                color: isGranted
                    ? AppColors.TEXT_PRIMARY
                    : AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
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
