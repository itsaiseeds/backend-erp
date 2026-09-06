import 'package:flutter/material.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';

class DashboardStatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String caption;
  final bool isAccented;

  const DashboardStatTile({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    required this.caption,
    this.isAccented = false,
  });

  @override
  Widget build(BuildContext context) {
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
            height: AppSizes.statTileAccent,
            color: isAccented ? AppColors.PRIMARY : AppColors.BORDER,
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    Container(
                      width: AppSizes.sidebarToggleTile,
                      height: AppSizes.sidebarToggleTile,
                      alignment: Alignment.center,
                      decoration: const BoxDecoration(
                        color: AppColors.PRIMARY_SURFACE,
                        borderRadius: BorderRadius.all(
                          Radius.circular(AppRadius.sm),
                        ),
                      ),
                      child: Icon(
                        icon,
                        size: AppSizes.iconMd,
                        color: AppColors.PRIMARY,
                      ),
                    ),
                    const SizedBox(width: AppSpacing.smd),
                    Expanded(
                      child: Text(
                        label,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.bodySmall.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.TEXT_SECONDARY,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpacing.md),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.headingMedium.copyWith(
                    letterSpacing: -0.6,
                    height: 1.1,
                  ),
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  caption,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.caption,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
