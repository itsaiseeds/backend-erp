import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../data/models/purchase_tracking_model.dart';
import '../bloc/purchase_tracking_cubit.dart';

const int _NAME_MAX_LENGTH = 255;
const int _COMPANY_NAME_MAX_LENGTH = 255;

class PurchaseTrackingFormDialog extends StatefulWidget {
  const PurchaseTrackingFormDialog({super.key});

  static Future<void> show(
    BuildContext context, {
    required PurchaseTrackingCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<PurchaseTrackingCubit>.value(
        value: cubit,
        child: const PurchaseTrackingFormDialog(),
      ),
    );
  }

  @override
  State<PurchaseTrackingFormDialog> createState() =>
      _PurchaseTrackingFormDialogState();
}

class _PurchaseTrackingFormDialogState
    extends State<PurchaseTrackingFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _descriptionController =
      TextEditingController();
  final TextEditingController _companyNameController =
      TextEditingController();
  final TextEditingController _priceController = TextEditingController();
  final TextEditingController _quantityController = TextEditingController();

  String _unit = NonStockUnit.KG;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _nameController.dispose();
    _descriptionController.dispose();
    _companyNameController.dispose();
    _priceController.dispose();
    _quantityController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final PurchaseTrackingCubit cubit = context.read<PurchaseTrackingCubit>();

    final bool succeeded = await cubit.createEntry(
      name: _nameController.text,
      description: _descriptionController.text,
      companyName: _companyNameController.text,
      price: _priceController.text,
      quantity: _quantityController.text,
      unit: _unit,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        AppStrings.PURCHASE_TRACKING_CREATED_TITLE,
      );
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
      icon: Icons.shopping_bag_outlined,
      title: AppStrings.ADD_PURCHASE_TRACKING_ENTRY,
      subtitle: AppStrings.ADD_PURCHASE_TRACKING_SUBTITLE,
      submitLabel: AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            AppTextField(
              controller: _nameController,
              label: AppStrings.FIELD_NAME,
              enabled: !_isSubmitting,
              inputFormatters: [
                LengthLimitingTextInputFormatter(_NAME_MAX_LENGTH),
              ],
              validator: FormValidators.requiredField,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _companyNameController,
              label: AppStrings.COLUMN_COMPANY_NAME,
              hint: AppStrings.FIELD_COMPANY_NAME_HINT,
              enabled: !_isSubmitting,
              inputFormatters: [
                LengthLimitingTextInputFormatter(_COMPANY_NAME_MAX_LENGTH),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _descriptionController,
              label: AppStrings.FIELD_DESCRIPTION,
              hint: AppStrings.FIELD_DESCRIPTION_HINT,
              enabled: !_isSubmitting,
              maxLines: 3,
            ),
            const SizedBox(height: AppSpacing.md),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: AppTextField(
                    controller: _quantityController,
                    label: AppStrings.COLUMN_QUANTITY,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    enabled: !_isSubmitting,
                    inputFormatters: [
                      FilteringTextInputFormatter.allow(
                        RegExp(r'^\d*\.?\d{0,3}'),
                      ),
                    ],
                    validator: FormValidators.positiveAmount,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: SearchableField<String>(
                    label: AppStrings.FIELD_UNIT,
                    hintText: AppStrings.FIELD_UNIT_HINT,
                    value: _unit,
                    items: NonStockUnit.ALL,
                    itemToString: (unit) => unit,
                    isSame: (a, b) => a == b,
                    isRequired: true,
                    enabled: !_isSubmitting,
                    onSelected: (unit) => setState(() => _unit = unit),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _priceController,
              label: AppStrings.FIELD_PRICE,
              hint: AppStrings.FIELD_PRICE_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
              ],
              validator: FormValidators.optionalNonNegativeAmount,
            ),
          ],
        ),
      ),
    );
  }
}
