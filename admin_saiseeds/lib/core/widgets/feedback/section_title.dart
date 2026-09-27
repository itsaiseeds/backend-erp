import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class SectionTitle extends StatelessWidget {
  final String title;
  final String? subtitle;
  final IconData? icon;
  final Widget? trailing;
  final bool hasRule;

  const SectionTitle({
    super.key,
    required this.title,
    this.subtitle,
    this.icon,
    this.trailing,
    this.hasRule = false,
  });

  @override
  Widget build(BuildContext context) {
    final IconData? leading = icon;
    final String? caption = subtitle;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        if (leading != null) ...[
          Icon(leading, size: AppSizes.iconLg, color: AppColors.PRIMARY),
          const SizedBox(width: AppSpacing.sm),
        ],
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelStrong,
              ),
              if (caption != null) ...[
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  caption,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ],
            ],
          ),
        ),
        if (trailing != null) ...[
          const SizedBox(width: AppSpacing.sm),
          trailing!,
        ],
        if (hasRule) ...[
          const SizedBox(width: AppSpacing.smd),
          const Expanded(child: Divider(color: AppColors.DIVIDER)),
        ],
      ],
    );
  }
}
