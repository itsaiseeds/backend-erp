import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppDropdown<T> extends StatelessWidget {
  final String? label;
  final String? hint;
  final T? value;
  final List<T> items;
  final String Function(T item) itemLabel;
  final ValueChanged<T?>? onChanged;
  final String? errorText;
  final bool enabled;

  const AppDropdown({
    super.key,
    this.label,
    this.hint,
    required this.value,
    required this.items,
    required this.itemLabel,
    this.onChanged,
    this.errorText,
    this.enabled = true,
  });

  OutlineInputBorder _border(Color color, {double width = 1}) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide(color: color, width: width),
      );

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null) ...[
          Text(label!, style: AppTypography.label),
          const SizedBox(height: AppSpacing.xs),
        ],
        DropdownButtonFormField<T>(
          initialValue: value,
          isExpanded: true,
          icon: const Icon(
            Icons.keyboard_arrow_down_rounded,
            color: AppColors.TEXT_SECONDARY,
          ),
          style: AppTypography.bodyMedium,
          dropdownColor: AppColors.SURFACE,
          borderRadius: BorderRadius.circular(AppRadius.md),
          onChanged: enabled ? onChanged : null,
          items: items
              .map(
                (item) => DropdownMenuItem<T>(
                  value: item,
                  child: Text(itemLabel(item), overflow: TextOverflow.ellipsis),
                ),
              )
              .toList(),
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            hintStyle: AppTypography.bodyMedium.copyWith(
              color: AppColors.TEXT_DISABLED,
            ),
            filled: true,
            fillColor: enabled ? AppColors.SURFACE : AppColors.SURFACE_VARIANT,
            contentPadding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm,
            ),
            border: _border(AppColors.BORDER),
            enabledBorder: _border(AppColors.BORDER),
            focusedBorder: _border(AppColors.BORDER_FOCUSED, width: 1.5),
            disabledBorder: _border(AppColors.BORDER),
            errorBorder: _border(AppColors.ERROR),
            focusedErrorBorder: _border(AppColors.ERROR, width: 1.5),
          ),
        ),
      ],
    );
  }
}
