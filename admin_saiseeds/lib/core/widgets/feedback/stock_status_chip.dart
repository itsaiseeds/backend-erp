import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class StockStatusChip extends StatelessWidget {
  final bool isComplete;

  const StockStatusChip({super.key, required this.isComplete});

  @override
  Widget build(BuildContext context) {
    final Color accent = isComplete
        ? AppColors.SUCCESS
        : AppColors.TEXT_SECONDARY;
    final Color background = isComplete
        ? AppColors.SUCCESS_LIGHT
        : AppColors.SURFACE_VARIANT;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: background,
        border: Border.all(
          color: isComplete ? AppColors.SUCCESS_BORDER : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isComplete
                ? Icons.check_circle_outline_rounded
                : Icons.pending_outlined,
            size: AppSizes.iconSm,
            color: accent,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            isComplete
                ? AppStrings.STOCK_UPDATED
                : AppStrings.STOCK_NOT_UPDATED,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.button.copyWith(color: accent),
          ),
        ],
      ),
    );
  }
}
