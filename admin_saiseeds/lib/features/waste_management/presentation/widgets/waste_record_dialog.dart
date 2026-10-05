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
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/waste_model.dart';
import '../bloc/waste_management_cubit.dart';

const int _REASON_MAX_LENGTH = 255;

class WasteRecordDialog extends StatefulWidget {
  final WasteModel waste;
  final RecordDialogMode initialMode;

  const WasteRecordDialog({
    super.key,
    required this.waste,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    WasteModel waste, {
    required WasteManagementCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<WasteManagementCubit>.value(
        value: cubit,
        child: WasteRecordDialog(waste: waste, initialMode: initialMode),
      ),
    );
  }

  @override
  State<WasteRecordDialog> createState() => _WasteRecordDialogState();
}

class _WasteRecordDialogState extends State<WasteRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _productController;
  late final TextEditingController _quantityController;
  late final TextEditingController _reasonController;
  late final TextEditingController _createdAtController;
  late final TextEditingController _createdByController;
  late final TextEditingController _referenceController;

  late RecordDialogMode _mode;
  bool _isSubmitting = false;

  WasteModel get _waste => widget.waste;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _productController = TextEditingController(text: _waste.productName);
    _quantityController = TextEditingController(text: _waste.quantityKg);
    _reasonController = TextEditingController(text: _waste.reason);
    _createdAtController = TextEditingController(
      text: DateFormatter.label(_waste.createdAt),
    );
    _createdByController = TextEditingController(text: _waste.createdByName);
    _referenceController = TextEditingController(text: _waste.publicId);
  }

  @override
  void dispose() {
    _productController.dispose();
    _quantityController.dispose();
    _reasonController.dispose();
    _createdAtController.dispose();
    _createdByController.dispose();
    _referenceController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _quantityController.text = _waste.quantityKg;
    _reasonController.text = _waste.reason;

    setState(() => _mode = RecordDialogMode.view);
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final WasteManagementCubit cubit = context.read<WasteManagementCubit>();

    final bool succeeded = await cubit.updateWaste(
      publicId: _waste.publicId,
      quantityKg: _quantityController.text.trim(),
      reason: _reasonController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.WASTE_UPDATED_TITLE);
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
      icon: Icons.delete_sweep_outlined,
      title: AppStrings.WASTE_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.EDIT_WASTE_SUBTITLE
          : AppStrings.WASTE_DETAIL_SUBTITLE,
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
            controller: _productController,
            label: AppStrings.COLUMN_PRODUCT,
            isEditable: false,
            isLocked: true,
          ),
          right: RecordField(
            controller: _quantityController,
            label: AppStrings.COLUMN_QUANTITY_KG,
            isEditable: _canEdit,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
            ],
            validator: FormValidators.positiveAmount,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _reasonController,
            label: AppStrings.COLUMN_REASON,
            hint: AppStrings.FIELD_REASON_HINT,
            isEditable: _canEdit,
            inputFormatters: [
              LengthLimitingTextInputFormatter(_REASON_MAX_LENGTH),
            ],
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
