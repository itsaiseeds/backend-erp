import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppToggleField extends StatelessWidget {
  final String label;
  final String? description;
  final bool value;
  final ValueChanged<bool>? onChanged;

  const AppToggleField({
    super.key,
    required this.label,
    required this.value,
    required this.onChanged,
    this.description,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.smd,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: AppTypography.label),
                if (description != null) ...[
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    description!,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_DISABLED,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.smd),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: AppColors.WHITE,
            activeTrackColor: AppColors.PRIMARY,
            inactiveThumbColor: AppColors.WHITE,
            inactiveTrackColor: AppColors.BORDER_STRONG,
            trackOutlineColor: const WidgetStatePropertyAll<Color>(
              AppColors.TRANSPARENT,
            ),
          ),
        ],
      ),
    );
  }
}
