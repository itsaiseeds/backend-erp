import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/initials_formatter.dart';
import '../../../../core/widgets/feedback/app_badge.dart';

class ProfileIdentityCard extends StatelessWidget {
  final String name;
  final String roleLabel;
  final String phoneNumber;
  final bool isCompact;

  const ProfileIdentityCard({
    super.key,
    required this.name,
    required this.roleLabel,
    required this.phoneNumber,
    this.isCompact = false,
  });

  @override
  Widget build(BuildContext context) {
    final double avatarSize = isCompact
        ? AppSizes.profileAvatarCompact
        : AppSizes.profileAvatar;

    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.fromBorderSide(
          BorderSide(color: AppColors.BORDER, width: AppSizes.borderThin),
        ),
        borderRadius: BorderRadius.all(Radius.circular(AppRadius.lg)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: EdgeInsets.all(isCompact ? AppSpacing.lgs : AppSpacing.lg),
            decoration: const BoxDecoration(
              color: AppColors.PRIMARY_SURFACE,
              border: Border(
                bottom: BorderSide(
                  color: AppColors.BORDER,
                  width: AppSizes.borderThin,
                ),
              ),
              borderRadius: BorderRadius.vertical(
                top: Radius.circular(AppRadius.lg),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  width: avatarSize,
                  height: avatarSize,
                  alignment: Alignment.center,
                  decoration: const BoxDecoration(
                    color: AppColors.SURFACE,
                    border: Border.fromBorderSide(
                      BorderSide(
                        color: AppColors.PRIMARY,
                        width: AppSizes.borderMedium,
                      ),
                    ),
                    borderRadius: BorderRadius.all(
                      Radius.circular(AppRadius.md),
                    ),
                  ),
                  child: Text(
                    InitialsFormatter.fromName(name),
                    style: AppTypography.headingMedium.copyWith(
                      color: AppColors.PRIMARY,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                SizedBox(width: isCompact ? AppSpacing.md : AppSpacing.lg),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        AppStrings.PROFILE_EYEBROW,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.labelStrong.copyWith(
                          color: AppColors.PRIMARY,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Text(
                        name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.headingMedium.copyWith(
                          letterSpacing: -0.6,
                          height: 1.1,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.smd),
                      Wrap(
                        spacing: AppSpacing.sm,
                        runSpacing: AppSpacing.sm,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          AppBadge(
                            label: roleLabel,
                            variant: AppBadgeVariant.success,
                          ),
                          _PhoneChip(phoneNumber: phoneNumber),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isCompact ? AppSpacing.lgs : AppSpacing.lg,
              vertical: AppSpacing.smd,
            ),
            child: Text(
              AppStrings.PROFILE_SUBHEADING,
              style: AppTypography.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}

class _PhoneChip extends StatelessWidget {
  final String phoneNumber;

  const _PhoneChip({required this.phoneNumber});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xs,
      ),
      decoration: const BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.fromBorderSide(
          BorderSide(color: AppColors.BORDER, width: AppSizes.borderThin),
        ),
        borderRadius: BorderRadius.all(Radius.circular(AppRadius.full)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.call_outlined,
            size: AppSizes.iconSm,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            phoneNumber,
            style: AppTypography.caption.copyWith(
              fontWeight: FontWeight.w600,
              color: AppColors.TEXT_PRIMARY,
            ),
          ),
        ],
      ),
    );
  }
}
