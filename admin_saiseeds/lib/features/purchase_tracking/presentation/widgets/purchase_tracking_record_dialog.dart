import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/purchase_tracking_model.dart';
import '../bloc/purchase_tracking_cubit.dart';

const int _NAME_MAX_LENGTH = 255;
const int _COMPANY_NAME_MAX_LENGTH = 255;

class PurchaseTrackingRecordDialog extends StatefulWidget {
  final PurchaseTrackingModel entry;
  final RecordDialogMode initialMode;

  const PurchaseTrackingRecordDialog({
    super.key,
    required this.entry,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    PurchaseTrackingModel entry, {
    required PurchaseTrackingCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<PurchaseTrackingCubit>.value(
        value: cubit,
        child: PurchaseTrackingRecordDialog(
          entry: entry,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<PurchaseTrackingRecordDialog> createState() =>
      _PurchaseTrackingRecordDialogState();
}

class _PurchaseTrackingRecordDialogState
    extends State<PurchaseTrackingRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _companyNameController;
  late final TextEditingController _descriptionController;
  late final TextEditingController _quantityController;
  late final TextEditingController _priceController;
  late final TextEditingController _createdAtController;
  late final TextEditingController _createdByController;
  late final TextEditingController _referenceController;

  late String _unit;
  late RecordDialogMode _mode;
  bool _isSubmitting = false;

  PurchaseTrackingModel get _entry => widget.entry;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _unit = _entry.unit;
    _nameController = TextEditingController(text: _entry.name);
    _companyNameController = TextEditingController(text: _entry.companyName);
    _descriptionController = TextEditingController(text: _entry.description);
    _quantityController = TextEditingController(text: _entry.quantity);
    _priceController = TextEditingController(text: _entry.price ?? '');
    _createdAtController = TextEditingController(
      text: DateFormatter.label(_entry.createdAt),
    );
    _createdByController = TextEditingController(text: _entry.createdByName);
    _referenceController = TextEditingController(text: _entry.publicId);
  }

  @override
  void dispose() {
    _nameController.dispose();
    _companyNameController.dispose();
    _descriptionController.dispose();
    _quantityController.dispose();
    _priceController.dispose();
    _createdAtController.dispose();
    _createdByController.dispose();
    _referenceController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _nameController.text = _entry.name;
    _companyNameController.text = _entry.companyName;
    _descriptionController.text = _entry.description;
    _quantityController.text = _entry.quantity;
    _priceController.text = _entry.price ?? '';
    _unit = _entry.unit;

    setState(() => _mode = RecordDialogMode.view);
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final PurchaseTrackingCubit cubit = context.read<PurchaseTrackingCubit>();

    final bool succeeded = await cubit.updateEntry(
      publicId: _entry.publicId,
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
        AppStrings.PURCHASE_TRACKING_UPDATED_TITLE,
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
    return AppRecordDialog(
      icon: Icons.shopping_bag_outlined,
      title: AppStrings.PURCHASE_TRACKING_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.EDIT_PURCHASE_TRACKING_SUBTITLE
          : AppStrings.PURCHASE_TRACKING_DETAIL_SUBTITLE,
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
          left: RecordField(
            controller: _nameController,
            label: AppStrings.FIELD_NAME,
            isEditable: _canEdit,
            inputFormatters: [
              LengthLimitingTextInputFormatter(_NAME_MAX_LENGTH),
            ],
            validator: FormValidators.requiredField,
          ),
          right: RecordField(
            controller: _companyNameController,
            label: AppStrings.COLUMN_COMPANY_NAME,
            isEditable: _canEdit,
            inputFormatters: [
              LengthLimitingTextInputFormatter(_COMPANY_NAME_MAX_LENGTH),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _descriptionController,
            label: AppStrings.FIELD_DESCRIPTION,
            isEditable: _canEdit,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _quantityController,
            label: AppStrings.COLUMN_QUANTITY,
            isEditable: _canEdit,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
            ],
            validator: FormValidators.positiveAmount,
          ),
          right: _isEditing
              ? SearchableField<String>(
                  label: AppStrings.FIELD_UNIT,
                  hintText: AppStrings.FIELD_UNIT_HINT,
                  value: _unit,
                  items: NonStockUnit.ALL,
                  itemToString: (unit) => unit,
                  isSame: (a, b) => a == b,
                  isRequired: true,
                  enabled: _canEdit,
                  onSelected: (unit) => setState(() => _unit = unit),
                )
              : RecordField(
                  controller: TextEditingController(text: _unit),
                  label: AppStrings.COLUMN_UNIT,
                  isEditable: false,
                  isLocked: true,
                ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _priceController,
            label: AppStrings.FIELD_PRICE,
            hint: AppStrings.FIELD_PRICE_HINT,
            isEditable: _canEdit,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
            ],
            validator: FormValidators.optionalNonNegativeAmount,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _createdAtController,
            label: AppStrings.COLUMN_CREATED_AT,
            isEditable: false,
            isLocked: true,
          ),
          right: RecordField(
            controller: _createdByController,
            label: AppStrings.COLUMN_CREATED_BY,
            isEditable: false,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _referenceController,
            label: AppStrings.COLUMN_REFERENCE,
            isEditable: false,
            isLocked: true,
          ),
        ),
      ],
    );
  }
}
