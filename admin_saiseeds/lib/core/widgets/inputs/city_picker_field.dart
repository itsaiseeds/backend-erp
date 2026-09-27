import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../models/city_model.dart';
import '../../services/metadata_service.dart';
import 'searchable_field.dart';

class CityPickerField extends StatelessWidget {
  final CityModel? value;
  final ValueChanged<CityModel> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const CityPickerField({
    super.key,
    required this.value,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
  });

  static String label(CityModel city) =>
      city.stateName.isEmpty ? city.name : '${city.name}, ${city.stateName}';

  @override
  Widget build(BuildContext context) {
    final List<CityModel> cities = MetadataService.instance.cities;

    return SearchableField<CityModel>(
      label: AppStrings.FIELD_CITY,
      hintText: AppStrings.FIELD_CITY_HINT,
      value: value,
      items: cities,
      itemToString: label,
      isSame: (a, b) => a.id == b.id,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
      helperText: cities.isEmpty ? AppStrings.CITIES_UNAVAILABLE : null,
      emptyHint: AppStrings.CITIES_UNAVAILABLE,
    );
  }
}
