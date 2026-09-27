import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/other_raw_materials/data/models/other_material_type_model.dart';
import 'searchable_field.dart';

class MaterialTypePickerField extends StatelessWidget {
  final OtherMaterialTypeModel? value;
  final List<OtherMaterialTypeModel> types;
  final ValueChanged<OtherMaterialTypeModel> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const MaterialTypePickerField({
    super.key,
    required this.value,
    required this.types,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
  });

  static String label(OtherMaterialTypeModel type) =>
      type.unitType.trim().isEmpty
      ? type.name
      : '${type.name} (${type.unitType})';

  static String searchText(OtherMaterialTypeModel type) =>
      '${type.name} ${type.unitType}';

  @override
  Widget build(BuildContext context) {
    return SearchableField<OtherMaterialTypeModel>(
      label: AppStrings.FIELD_MATERIAL_TYPE,
      hintText: AppStrings.FIELD_MATERIAL_TYPE_HINT,
      value: value,
      items: types,
      itemToString: label,
      searchText: searchText,
      isSame: (a, b) => a.id == b.id,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
    );
  }
}
