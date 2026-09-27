import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/material_types_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/material_type_picker_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../products/data/models/product_model.dart';
import '../../data/models/other_material_type_model.dart';
import '../bloc/other_raw_materials_cubit.dart';

class RecipeFormDialog extends StatefulWidget {
  const RecipeFormDialog({super.key});

  static Future<void> show(
    BuildContext context, {
    required OtherRawMaterialsCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OtherRawMaterialsCubit>.value(
        value: cubit,
        child: const RecipeFormDialog(),
      ),
    );
  }

  @override
  State<RecipeFormDialog> createState() => _RecipeFormDialogState();
}

class _RecipeFormDialogState extends State<RecipeFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _packetWeightController =
      TextEditingController();
  final TextEditingController _quantityController = TextEditingController();

  ProductModel? _product;
  OtherMaterialTypeModel? _materialType;

  bool _isSubmitting = false;
  String? _productError;
  String? _materialTypeError;

  @override
  void dispose() {
    _packetWeightController.dispose();
    _quantityController.dispose();
    super.dispose();
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

    final bool succeeded = await cubit.createRecipe(
      productPublicId: _product!.publicId,
      materialTypeId: _materialType!.id,
      packetWeight: _packetWeightController.text.trim(),
      quantity: _quantityController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.RECIPE_CREATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.layers_outlined,
      title: AppStrings.ADD_RECIPE,
      subtitle: AppStrings.ADD_RECIPE_SUBTITLE,
      submitLabel: AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            ProductPickerField(
              value: _product,
              products: ProductsService.instance.products,
              enabled: !_isSubmitting,
              errorText: _productError,
              onSelected: (product) => setState(() {
                _product = product;
                _productError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            MaterialTypePickerField(
              value: _materialType,
              types: MaterialTypesService.instance.types,
              enabled: !_isSubmitting,
              errorText: _materialTypeError,
              onSelected: (type) => setState(() {
                _materialType = type;
                _materialTypeError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _packetWeightController,
              label: AppStrings.COLUMN_PACKET_WEIGHT,
              hint: AppStrings.FIELD_PACKET_WEIGHT_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
              ],
              validator: FormValidators.positiveAmount,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _quantityController,
              label: AppStrings.FIELD_RECIPE_QUANTITY,
              hint: AppStrings.FIELD_RECIPE_QUANTITY_HINT,
              helperText: _materialType?.unitType,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
              ],
              validator: FormValidators.positiveAmount,
            ),
          ],
        ),
      ),
    );
  }
}
