import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../models/crop_model.dart';
import 'searchable_field.dart';

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
  final VoidCallback? onBlockedTap;
  final bool isUnavailable;

  const CropPickerField({
    super.key,
    required this.value,
    required this.crops,
    required this.onSelected,
    required this.onCreateRequested,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
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
        .where(
          (crop) =>
              needle.isEmpty ||
              crop.name.toLowerCase().contains(needle.toLowerCase()),
        )
        .map(CropPickerOption.existing)
        .toList();

    if (needle.isEmpty) return options;

    final bool hasExactMatch = crops.any(
      (crop) => crop.name.trim().toLowerCase() == needle.toLowerCase(),
    );
    if (hasExactMatch) return options;

    return [CropPickerOption.create(needle), ...options];
  }

  void _handleSelected(CropPickerOption option) {
    if (option.isCreate) {
      onCreateRequested(option.createName);
      return;
    }
    onSelected(option.crop!);
  }

  @override
  Widget build(BuildContext context) {
    final CropModel? current = value;

    return SearchableField<CropPickerOption>(
      label: AppStrings.FIELD_CROP,
      hintText: AppStrings.FIELD_CROP_HINT,
      value: current == null ? null : CropPickerOption.existing(current),
      items: crops.map(CropPickerOption.existing).toList(),
      itemToString: optionLabel,
      optionsBuilder: (query) => optionsFor(crops: crops, query: query),
      isSame: (a, b) => !a.isCreate && !b.isCreate && a.crop!.id == b.crop!.id,
      onSelected: _handleSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
      helperText: isUnavailable ? AppStrings.CROPS_UNAVAILABLE : null,
    );
  }
}
