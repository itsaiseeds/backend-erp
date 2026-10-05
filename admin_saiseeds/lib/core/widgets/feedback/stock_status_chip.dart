import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

/// Icon-only status marker sized to match the square icon buttons beside it.
///
/// The state is carried by the tooltip rather than a label: the bar has room
/// for one more square, not for a word that grows with the status text.
class StockStatusChip extends StatelessWidget {
  final bool isComplete;

  const StockStatusChip({super.key, required this.isComplete});

  @override
  Widget build(BuildContext context) {
    final Color accent = isComplete
        ? AppColors.SUCCESS
        : AppColors.TEXT_SECONDARY;

    return Tooltip(
      message: isComplete
          ? AppStrings.STOCK_UPDATED
          : AppStrings.STOCK_NOT_UPDATED,
      child: Padding(
        padding: const EdgeInsets.all(AppSizes.actionButtonInset),
        child: Container(
          width: double.infinity,
          height: double.infinity,
          decoration: BoxDecoration(
            color: isComplete ? AppColors.SUCCESS_LIGHT : AppColors.TRANSPARENT,
            border: Border.all(
              color: isComplete ? AppColors.SUCCESS_BORDER : AppColors.BORDER,
            ),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          alignment: Alignment.center,
          child: Icon(
            isComplete
                ? Icons.check_circle_outline_rounded
                : Icons.pending_outlined,
            size: AppSizes.iconLg,
            color: accent,
          ),
        ),
      ),
    );
  }
}
