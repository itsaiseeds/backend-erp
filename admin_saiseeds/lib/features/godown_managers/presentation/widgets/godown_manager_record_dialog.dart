import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/formatters/role_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/totp_qr_panel.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/godown_manager_model.dart';
import '../bloc/godown_managers_cubit.dart';

class GodownManagerRecordDialog extends StatefulWidget {
  final GodownManagerModel godownManager;
  final RecordDialogMode initialMode;

  const GodownManagerRecordDialog({
    super.key,
    required this.godownManager,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    GodownManagerModel manager, {
    required GodownManagersCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<GodownManagersCubit>.value(
        value: cubit,
        child: GodownManagerRecordDialog(
          godownManager: manager,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<GodownManagerRecordDialog> createState() =>
      _GodownManagerRecordDialogState();
}

class _GodownManagerRecordDialogState
    extends State<GodownManagerRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;
  late final TextEditingController _roleController;
  late final TextEditingController _createdByController;
  late final TextEditingController _createdAtController;

  late RecordDialogMode _mode;
  bool _isSubmitting = false;

  GodownManagerModel get _manager => widget.godownManager;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _nameController = TextEditingController(text: _manager.name);
    _emailController = TextEditingController(text: _manager.email);
    _phoneController = TextEditingController(text: _manager.phoneNumber);
    _roleController = TextEditingController(
      text: RoleFormatter.label(_manager.role),
    );
    _createdByController = TextEditingController(text: _manager.createdByName);
    _createdAtController = TextEditingController(
      text: DateFormatter.label(_manager.createdAt),
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    _roleController.dispose();
    _createdByController.dispose();
    _createdAtController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _nameController.text = _manager.name;
    _emailController.text = _manager.email;
    _phoneController.text = _manager.phoneNumber;
    setState(() => _mode = RecordDialogMode.view);
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final GodownManagersCubit cubit = context.read<GodownManagersCubit>();
    final String email = _emailController.text.trim();

    final bool succeeded = await cubit.updateGodownManager(
      id: _manager.id,
      name: _nameController.text.trim(),
      phoneNumber: _phoneController.text.trim(),
      email: email.isEmpty ? null : email,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.GODOWN_MANAGER_UPDATED_TITLE);
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
      icon: Icons.warehouse_outlined,
      title: AppStrings.GODOWN_MANAGER_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.GODOWN_MANAGER_EDIT_HINT
          : AppStrings.DETAIL_SECTION_ACCOUNT_HINT,
      mode: _mode,
      body: Form(key: _formKey, child: _buildFields()),
      onEdit: _enterEditMode,
      onCancelEdit: _cancelEdit,
      onSubmit: _isSubmitting ? null : _submit,
      isSubmitting: _isSubmitting,
      submitLabel: AppStrings.UPDATE,
      aside: RecordDialogAside(
        title: AppStrings.DETAIL_SECTION_AUTHENTICATOR,
        subtitle: AppStrings.DETAIL_SECTION_AUTHENTICATOR_HINT,
        child: TotpQrPanel(
          provisioningUri: _manager.provisioningUri,
          phoneNumber: _manager.phoneNumber,
          subjectName: _manager.name,
          isStacked: true,
          isBlurred: _manager.isAdmin,
        ),
      ),
    );
  }

  Widget _buildFields() {
    final bool canEdit = _isEditing && !_isSubmitting;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: RecordField(
            controller: _nameController,
            label: AppStrings.FIELD_NAME,
            hint: AppStrings.FIELD_NAME_HINT,
            isEditable: canEdit,
            validator: FormValidators.requiredField,
          ),
          right: RecordField(
            controller: _emailController,
            label: AppStrings.FIELD_EMAIL_OPTIONAL,
            hint: AppStrings.FIELD_EMAIL_HINT,
            keyboardType: TextInputType.emailAddress,
            isEditable: canEdit,
            validator: FormValidators.optionalEmail,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _phoneController,
            label: AppStrings.COLUMN_PHONE_NUMBER,
            hint: AppStrings.FIELD_PHONE_HINT,
            keyboardType: TextInputType.phone,
            isEditable: canEdit,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(
                FormValidators.PHONE_NUMBER_LENGTH,
              ),
            ],
            validator: FormValidators.phoneNumber,
          ),
          right: RecordField(
            controller: _roleController,
            label: AppStrings.COLUMN_ROLE,
            isEditable: canEdit,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _createdByController,
            label: AppStrings.DETAIL_FIELD_CREATED_BY,
            isEditable: canEdit,
            isLocked: true,
          ),
          right: RecordField(
            controller: _createdAtController,
            label: AppStrings.DETAIL_FIELD_CREATED_AT,
            isEditable: canEdit,
            isLocked: true,
          ),
        ),
      ],
    );
  }
}
