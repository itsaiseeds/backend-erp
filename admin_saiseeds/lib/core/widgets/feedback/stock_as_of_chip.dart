import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/formatters/date_formatter.dart';

class StockAsOfChip extends StatelessWidget {
  final String isoDate;

  const StockAsOfChip({super.key, required this.isoDate});

  @override
  Widget build(BuildContext context) {
    final DateTime? parsed = DateTime.tryParse(isoDate.trim());
    if (parsed == null) return const SizedBox.shrink();

    // Centred rather than stretched: the chip is a label beside the search
    // bar, so it keeps its own height instead of matching the row's.
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: AppColors.SURFACE_VARIANT,
          border: Border.all(color: AppColors.BORDER),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.event_available_outlined,
              size: AppSizes.iconXs,
              color: AppColors.TEXT_SECONDARY,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              '${AppStrings.STOCK_AS_OF_PREFIX} '
              '${DateFormatter.dayLabel(parsed)}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.caption,
            ),
          ],
        ),
      ),
    );
  }
}
