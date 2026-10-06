import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/parties/data/models/party_model.dart';
import 'searchable_field.dart';

/// Two-option picker for a party's type (Raw Material / Other Material).
/// The wire value stays in [PartyType]; the menu shows the display label.
class PartyTypePickerField extends StatelessWidget {
  final String? value;
  final ValueChanged<String> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const PartyTypePickerField({
    super.key,
    required this.value,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
  });

  static String labelOf(String value) => switch (value) {
    PartyType.OTHER_MATERIAL => AppStrings.PARTY_TYPE_OTHER_MATERIAL,
    PartyType.RAW_MATERIAL => AppStrings.PARTY_TYPE_RAW_MATERIAL,
    _ => AppStrings.TABLE_VALUE_UNAVAILABLE,
  };

  @override
  Widget build(BuildContext context) {
    return SearchableField<String>(
      label: AppStrings.FIELD_PARTY_TYPE,
      hintText: AppStrings.FIELD_PARTY_TYPE_HINT,
      value: value,
      items: PartyType.values,
      itemToString: labelOf,
      isSame: (a, b) => a == b,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
      isRequired: true,
    );
  }
}