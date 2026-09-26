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

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.event_available_outlined,
            size: AppSizes.iconSm,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            '${AppStrings.STOCK_AS_OF_PREFIX} '
            '${DateFormatter.dayLabel(parsed)}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.button.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ),
    );
  }
}
