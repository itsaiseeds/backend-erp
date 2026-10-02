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

    // Centred rather than stretched: the chip is a label beside the search
    // bar, so it keeps its own height instead of matching the row's.
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: background,
          border: Border.all(
            color: isComplete ? AppColors.SUCCESS_BORDER : AppColors.BORDER,
          ),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isComplete
                  ? Icons.check_circle_outline_rounded
                  : Icons.pending_outlined,
              size: AppSizes.iconXs,
              color: accent,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              isComplete
                  ? AppStrings.STOCK_UPDATED
                  : AppStrings.STOCK_NOT_UPDATED,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.caption.copyWith(color: accent),
            ),
          ],
        ),
      ),
    );
  }
}
