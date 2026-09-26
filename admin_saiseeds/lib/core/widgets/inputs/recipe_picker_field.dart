import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/other_raw_materials/data/models/other_material_recipe_model.dart';
import 'searchable_field.dart';

class RecipePickerField extends StatelessWidget {
  final OtherMaterialRecipeModel? value;
  final List<OtherMaterialRecipeModel> recipes;
  final ValueChanged<OtherMaterialRecipeModel> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const RecipePickerField({
    super.key,
    required this.value,
    required this.recipes,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
  });

  static String label(OtherMaterialRecipeModel recipe) {
    final List<String> parts = [
      if (recipe.productName.trim().isNotEmpty) recipe.productName,
      if (recipe.materialTypeName.trim().isNotEmpty) recipe.materialTypeName,
    ];
    final String head = parts.isEmpty ? recipe.publicId : parts.join(' - ');

    if (recipe.packetWeight.trim().isEmpty) return head;
    return '$head (${recipe.packetWeight})';
  }

  static String searchText(OtherMaterialRecipeModel recipe) =>
      '${recipe.productName} ${recipe.materialTypeName} '
      '${recipe.packetWeight} ${recipe.unitType}';

  @override
  Widget build(BuildContext context) {
    return SearchableField<OtherMaterialRecipeModel>(
      label: AppStrings.FIELD_RECIPE,
      hintText: AppStrings.FIELD_RECIPE_HINT,
      value: value,
      items: recipes,
      itemToString: label,
      searchText: searchText,
      isSame: (a, b) => a.publicId == b.publicId,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
    );
  }
}
