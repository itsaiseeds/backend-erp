import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/material_types_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
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
  final RecordDialogMode initialMode;

  const RecipeRecordDialog({
    super.key,
    required this.recipe,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    OtherMaterialRecipeModel recipe, {
    required OtherRawMaterialsCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OtherRawMaterialsCubit>.value(
        value: cubit,
        child: RecipeRecordDialog(recipe: recipe, initialMode: initialMode),
      ),
    );
  }

  @override
  State<RecipeRecordDialog> createState() => _RecipeRecordDialogState();
}

class _RecipeRecordDialogState extends State<RecipeRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _packetWeightController;
  late final TextEditingController _quantityController;

  late RecordDialogMode _mode;
  ProductModel? _product;
  OtherMaterialTypeModel? _materialType;

  bool _isSubmitting = false;
  String? _productError;
  String? _materialTypeError;

  OtherMaterialRecipeModel get _recipe => widget.recipe;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  String get _quantityLabel {
    final String unit = _materialType?.unitType.trim() ?? '';
    if (unit.isEmpty) return AppStrings.FIELD_RECIPE_QUANTITY;
    return '${AppStrings.FIELD_RECIPE_QUANTITY} ($unit)';
  }

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _packetWeightController = TextEditingController(
      text: _recipe.packetWeight,
    );
    _quantityController = TextEditingController(text: _recipe.quantity);
    _product = _resolveProduct();
    _materialType = _resolveMaterialType();
  }

  ProductModel? _resolveProduct() =>
      ProductsService.instance.productByPublicId(_recipe.productPublicId);

  OtherMaterialTypeModel? _resolveMaterialType() =>
      MaterialTypesService.instance.typeById(_recipe.materialTypeId) ??
      _recipe.materialType;

  @override
  void dispose() {
    _packetWeightController.dispose();
    _quantityController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _packetWeightController.text = _recipe.packetWeight;
    _quantityController.text = _recipe.quantity;

    setState(() {
      _product = _resolveProduct();
      _materialType = _resolveMaterialType();
      _productError = null;
      _materialTypeError = null;
      _mode = RecordDialogMode.view;
    });
  }

  void _notifyViewMode() {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: AppStrings.VIEW_MODE_TOAST_BODY,
    );
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isProductValid = _product != null;
    final bool isTypeValid = _materialType != null;

    setState(() {
      _productError = isProductValid
          ? null
          : AppStrings.VALIDATION_PRODUCT_REQUIRED;
      _materialTypeError = isTypeValid
          ? null
          : AppStrings.VALIDATION_MATERIAL_TYPE_REQUIRED;
    });

    if (!isFormValid || !isProductValid || !isTypeValid) return;

    setState(() => _isSubmitting = true);

    final OtherRawMaterialsCubit cubit = context.read<OtherRawMaterialsCubit>();

    final bool succeeded = await cubit.updateRecipe(
      publicId: _recipe.publicId,
      productPublicId: _product!.publicId,
      materialTypeId: _materialType!.id,
      packetWeight: _packetWeightController.text.trim(),
      quantity: _quantityController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.RECIPE_UPDATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.layers_outlined,
      title: AppStrings.RECIPE_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.EDIT_RECIPE_SUBTITLE
          : AppStrings.RECIPE_DETAIL_SUBTITLE,
      mode: _mode,
      body: Form(key: _formKey, child: _buildFields()),
      onEdit: _enterEditMode,
      onCancelEdit: _cancelEdit,
      onSubmit: _isSubmitting ? null : _submit,
      isSubmitting: _isSubmitting,
      submitLabel: AppStrings.UPDATE,
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
            enabled: _canEdit,
            errorText: _productError,
            onBlockedTap: _notifyViewMode,
            isUnavailable: _product == null && _recipe.productName.isNotEmpty,
            onSelected: (product) => setState(() {
              _product = product;
              _productError = null;
            }),
          ),
          right: MaterialTypePickerField(
            value: _materialType,
            types: MaterialTypesService.instance.types,
            enabled: _canEdit,
            errorText: _materialTypeError,
            onBlockedTap: _notifyViewMode,
            onSelected: (type) => setState(() {
              _materialType = type;
              _materialTypeError = null;
            }),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _packetWeightController,
            label: AppStrings.COLUMN_PACKET_WEIGHT,
            hint: AppStrings.FIELD_PACKET_WEIGHT_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            isEditable: _canEdit,
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
            ],
            validator: FormValidators.positiveAmount,
          ),
          right: RecordField(
            controller: _quantityController,
            label: _quantityLabel,
            hint: AppStrings.FIELD_RECIPE_QUANTITY_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            isEditable: _canEdit,
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
            ],
            validator: FormValidators.positiveAmount,
          ),
        ),
      ],
    );
  }
}
