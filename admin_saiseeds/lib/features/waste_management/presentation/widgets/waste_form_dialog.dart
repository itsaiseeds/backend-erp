import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../products/data/models/product_model.dart';
import '../bloc/waste_management_cubit.dart';

const int _REASON_MAX_LENGTH = 255;

class WasteFormDialog extends StatefulWidget {
  const WasteFormDialog({super.key});

  static Future<void> show(
    BuildContext context, {
    required WasteManagementCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<WasteManagementCubit>.value(
        value: cubit,
        child: const WasteFormDialog(),
      ),
    );
  }

  @override
  State<WasteFormDialog> createState() => _WasteFormDialogState();
}

class _WasteFormDialogState extends State<WasteFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _quantityController = TextEditingController();
  final TextEditingController _reasonController = TextEditingController();

  ProductModel? _product;
  bool _isSubmitting = false;
  String? _productError;

  @override
  void dispose() {
    _quantityController.dispose();
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isProductValid = _product != null;

    setState(
      () => _productError = isProductValid
          ? null
          : AppStrings.VALIDATION_PRODUCT_REQUIRED,
    );

    if (!isFormValid || !isProductValid) return;

    setState(() => _isSubmitting = true);

    final WasteManagementCubit cubit = context.read<WasteManagementCubit>();

    final bool succeeded = await cubit.recordWaste(
      productPublicId: _product!.publicId,
      quantityKg: _quantityController.text.trim(),
      reason: _reasonController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.WASTE_CREATED_TITLE);
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
      icon: Icons.delete_sweep_outlined,
      title: AppStrings.ADD_WASTE,
      subtitle: AppStrings.ADD_WASTE_SUBTITLE,
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
            AppTextField(
              controller: _quantityController,
              label: AppStrings.FIELD_QUANTITY_KG,
              hint: AppStrings.FIELD_QUANTITY_KG_HINT,
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
              controller: _reasonController,
              label: AppStrings.FIELD_REASON,
              hint: AppStrings.FIELD_REASON_HINT,
              enabled: !_isSubmitting,
              inputFormatters: [
                LengthLimitingTextInputFormatter(_REASON_MAX_LENGTH),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
