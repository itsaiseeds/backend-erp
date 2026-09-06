import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../models/crop_model.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'searchable_popup_menu.dart';

class CropPickerOption {
  final CropModel? crop;
  final String createName;

  const CropPickerOption.existing(CropModel value)
    : crop = value,
      createName = '';

  const CropPickerOption.create(this.createName) : crop = null;

  bool get isCreate => crop == null;
}

class CropPickerField extends StatelessWidget {
  final CropModel? value;
  final List<CropModel> crops;
  final ValueChanged<CropModel> onSelected;
  final ValueChanged<String> onCreateRequested;
  final String? errorText;
  final bool enabled;
  final bool isUnavailable;

  const CropPickerField({
    super.key,
    required this.value,
    required this.crops,
    required this.onSelected,
    required this.onCreateRequested,
    this.errorText,
    this.enabled = true,
    this.isUnavailable = false,
  });

  static String label(CropModel crop) => crop.name;

  static String optionLabel(CropPickerOption option) => option.isCreate
      ? '${AppStrings.CROP_CREATE_OPTION_PREFIX} "${option.createName}"'
      : label(option.crop!);

  static String createConfirmationMessage(String name) =>
      '${AppStrings.CROP_CREATE_CONFIRM_BODY_PREFIX} "$name" '
      '${AppStrings.CROP_CREATE_CONFIRM_BODY_SUFFIX}';

  static List<CropPickerOption> optionsFor({
    required List<CropModel> crops,
    required String query,
  }) {
    final String needle = query.trim();
    final List<CropPickerOption> options = crops
        .map(CropPickerOption.existing)
        .toList();

    if (needle.isEmpty) return options;

    final bool hasExactMatch = crops.any(
      (crop) => crop.name.trim().toLowerCase() == needle.toLowerCase(),
    );
    if (hasExactMatch) return options;

    return [CropPickerOption.create(needle), ...options];
  }

  @override
  Widget build(BuildContext context) {
    final bool hasError = errorText != null && errorText!.isNotEmpty;

    final Widget field = Container(
      height: AppSizes.inputHeight,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: enabled ? AppColors.SURFACE : AppColors.SURFACE_VARIANT,
        border: Border.all(
          color: hasError ? AppColors.ERROR : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              value == null ? AppStrings.FIELD_CROP_HINT : label(value!),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodyMedium.copyWith(
                color: value == null
                    ? AppColors.TEXT_DISABLED
                    : AppColors.TEXT_PRIMARY,
              ),
            ),
          ),
          const Icon(
            Icons.keyboard_arrow_down_rounded,
            size: AppSizes.iconMd,
            color: AppColors.TEXT_SECONDARY,
          ),
        ],
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(AppStrings.FIELD_CROP, style: AppTypography.labelStrong),
        const SizedBox(height: AppSpacing.sm),
        if (enabled)
          SearchablePopupMenu<CropPickerOption>(
            items: crops.map(CropPickerOption.existing).toList(),
            itemToString: optionLabel,
            optionsBuilder: (query) => optionsFor(crops: crops, query: query),
            isSelected: (option) =>
                !option.isCreate && option.crop!.id == value?.id,
            onSelected: _handleSelected,
            child: field,
          )
        else
          field,
        if (isUnavailable) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.CROPS_UNAVAILABLE,
            style: AppTypography.caption.copyWith(color: AppColors.WARNING),
          ),
        ],
        if (hasError) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            errorText!,
            style: AppTypography.caption.copyWith(color: AppColors.ERROR),
          ),
        ],
      ],
    );
  }

  void _handleSelected(CropPickerOption option) {
    if (option.isCreate) {
      onCreateRequested(option.createName);
      return;
    }
    onSelected(option.crop!);
  }
}
