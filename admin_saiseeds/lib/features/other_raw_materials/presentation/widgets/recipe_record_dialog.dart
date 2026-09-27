import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/material_types_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/inputs/material_type_picker_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../../products/data/models/product_model.dart';
import '../../data/models/other_material_recipe_model.dart';
import '../../data/models/other_material_type_model.dart';
import '../bloc/other_raw_materials_cubit.dart';

class RecipeRecordDialog extends StatefulWidget {
  final OtherMaterialRecipeModel recipe;

  const RecipeRecordDialog({super.key, required this.recipe});

  static Future<void> show(
    BuildContext context,
    OtherMaterialRecipeModel recipe, {
    required OtherRawMaterialsCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OtherRawMaterialsCubit>.value(
        value: cubit,
        child: RecipeRecordDialog(recipe: recipe),
      ),
    );
  }

  @override
  State<RecipeRecordDialog> createState() => _RecipeRecordDialogState();
}

class _RecipeRecordDialogState extends State<RecipeRecordDialog> {
  late final TextEditingController _packetWeightController;
  late final TextEditingController _quantityController;

  ProductModel? _product;
  OtherMaterialTypeModel? _materialType;

  OtherMaterialRecipeModel get _recipe => widget.recipe;

  String get _quantityLabel {
    final String unit = _materialType?.unitType.trim() ?? '';
    if (unit.isEmpty) return AppStrings.FIELD_RECIPE_QUANTITY;
    return '${AppStrings.FIELD_RECIPE_QUANTITY} ($unit)';
  }

  @override
  void initState() {
    super.initState();
    _packetWeightController = TextEditingController(text: _recipe.packetWeight);
    _quantityController = TextEditingController(text: _recipe.quantity);
    _product = ProductsService.instance.productByPublicId(
      _recipe.productPublicId,
    );
    _materialType =
        MaterialTypesService.instance.typeById(_recipe.materialTypeId) ??
        _recipe.materialType;
  }

  @override
  void dispose() {
    _packetWeightController.dispose();
    _quantityController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.layers_outlined,
      title: AppStrings.RECIPE_DETAIL_TITLE,
      subtitle: AppStrings.RECIPE_DETAIL_SUBTITLE,
      mode: RecordDialogMode.view,
      body: _buildFields(),
    );
  }

  Widget _buildFields() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: ProductPickerField(
            value: _product,
            products: ProductsService.instance.products,
            enabled: false,
            isUnavailable: _product == null && _recipe.productName.isNotEmpty,
            onSelected: (_) {},
          ),
          right: MaterialTypePickerField(
            value: _materialType,
            types: MaterialTypesService.instance.types,
            enabled: false,
            onSelected: (_) {},
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _packetWeightController,
            label: AppStrings.COLUMN_PACKET_WEIGHT,
            isEditable: false,
            isLocked: true,
          ),
          right: RecordField(
            controller: _quantityController,
            label: _quantityLabel,
            isEditable: false,
            isLocked: true,
          ),
        ),
      ],
    );
  }
}
