import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';

class LoginCardHeader extends StatelessWidget {
  final bool isCompact;

  const LoginCardHeader({super.key, this.isCompact = false});

  @override
  Widget build(BuildContext context) {
    final double tileSize = isCompact
        ? AppSizes.brandMarkTileCompact
        : AppSizes.brandMarkTile;

    return Container(
      decoration: const BoxDecoration(
        color: AppColors.PRIMARY_SURFACE,
        border: Border(bottom: BorderSide(color: AppColors.BORDER)),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? AppSpacing.lgs : AppSpacing.lg,
        vertical: isCompact ? AppSpacing.md : AppSpacing.lgs,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Container(
            width: tileSize,
            height: tileSize,
            padding: const EdgeInsets.all(AppSizes.brandMarkInset),
            decoration: const BoxDecoration(
              color: AppColors.SURFACE,
              border: Border.fromBorderSide(
                BorderSide(color: AppColors.BORDER),
              ),
              borderRadius: BorderRadius.all(Radius.circular(AppRadius.md)),
            ),
            child: Image.asset(
              _logoAsset,
              fit: BoxFit.contain,
              filterQuality: FilterQuality.medium,
              semanticLabel: AppStrings.LOGIN_LOGO_LABEL,
            ),
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.LOGIN_EYEBROW,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.labelStrong.copyWith(
                    color: AppColors.PRIMARY,
                  ),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  AppStrings.LOGIN_HEADING,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.headingMedium.copyWith(
                    letterSpacing: -0.4,
                    height: 1.1,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static const String _logoAsset = 'assets/logo/saiseeds-logo.png';
}
