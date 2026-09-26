import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/parties_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/party_picker_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../parties/data/models/party_model.dart';
import '../../../products/data/models/product_model.dart';
import '../bloc/inward_raw_materials_cubit.dart';

class InwardFormDialog extends StatefulWidget {
  const InwardFormDialog({super.key});

  static final DateFormat isoDate = DateFormat('yyyy-MM-dd');

  static Future<void> show(
    BuildContext context, {
    required InwardRawMaterialsCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<InwardRawMaterialsCubit>.value(
        value: cubit,
        child: const InwardFormDialog(),
      ),
    );
  }

  @override
  State<InwardFormDialog> createState() => _InwardFormDialogState();
}

class _InwardFormDialogState extends State<InwardFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _quantityController = TextEditingController();

  ProductModel? _product;
  PartyModel? _party;
  DateTime? _labSamplingDate;

  bool _isSubmitting = false;
  String? _productError;
  String? _partyError;
  String? _dateError;

  @override
  void dispose() {
    _quantityController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isProductValid = _product != null;
    final bool isPartyValid = _party != null;
    final bool isDateValid = _labSamplingDate != null;

    setState(() {
      _productError = isProductValid
          ? null
          : AppStrings.VALIDATION_PRODUCT_REQUIRED;
      _partyError = isPartyValid ? null : AppStrings.VALIDATION_PARTY_REQUIRED;
      _dateError = isDateValid
          ? null
          : AppStrings.VALIDATION_LAB_DATE_REQUIRED;
    });

    if (!isFormValid || !isProductValid || !isPartyValid || !isDateValid) {
      return;
    }

    setState(() => _isSubmitting = true);

    final InwardRawMaterialsCubit cubit = context
        .read<InwardRawMaterialsCubit>();

    final bool succeeded = await cubit.createLot(
      productPublicId: _product!.publicId,
      partyId: _party!.id,
      quantityKg: _quantityController.text.trim(),
      labSamplingDate: InwardFormDialog.isoDate.format(_labSamplingDate!),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.INWARD_CREATED_TITLE);
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
      icon: Icons.local_shipping_outlined,
      title: AppStrings.ADD_INWARD,
      subtitle: AppStrings.ADD_INWARD_SUBTITLE,
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
            PartyPickerField(
              value: _party,
              parties: PartiesService.instance.parties,
              enabled: !_isSubmitting,
              errorText: _partyError,
              onSelected: (party) => setState(() {
                _party = party;
                _partyError = null;
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
            SingleDateField(
              label: AppStrings.FIELD_LAB_SAMPLING_DATE,
              value: _labSamplingDate,
              enabled: !_isSubmitting,
              onChanged: (date) => setState(() {
                _labSamplingDate = date;
                _dateError = null;
              }),
            ),
            if (_dateError != null) ...[
              const SizedBox(height: AppSpacing.xs),
              Text(
                _dateError!,
                style: Theme.of(context).inputDecorationTheme.errorStyle,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
