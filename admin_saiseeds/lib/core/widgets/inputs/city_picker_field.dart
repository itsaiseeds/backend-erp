import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../models/city_model.dart';
import '../../services/metadata_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'searchable_popup_menu.dart';

class CityPickerField extends StatelessWidget {
  final CityModel? value;
  final ValueChanged<CityModel> onSelected;
  final String? errorText;
  final bool enabled;

  const CityPickerField({
    super.key,
    required this.value,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
  });

  static String label(CityModel city) =>
      city.stateName.isEmpty ? city.name : '${city.name}, ${city.stateName}';

  @override
  Widget build(BuildContext context) {
    final List<CityModel> cities = MetadataService.instance.cities;
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
              value == null ? AppStrings.FIELD_CITY_HINT : label(value!),
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
        Text(AppStrings.FIELD_CITY, style: AppTypography.labelStrong),
        const SizedBox(height: AppSpacing.sm),
        if (enabled && cities.isNotEmpty)
          SearchablePopupMenu<CityModel>(
            items: cities,
            itemToString: label,
            isSelected: (city) => city.id == value?.id,
            onSelected: onSelected,
            child: field,
          )
        else
          field,
        if (cities.isEmpty) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.CITIES_UNAVAILABLE,
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
}
