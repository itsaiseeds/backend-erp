import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/formatters/role_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/totp_qr_panel.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/sales_person_model.dart';
import '../bloc/sales_people_cubit.dart';

class SalesPersonRecordDialog extends StatefulWidget {
  final SalesPersonModel salesPerson;
  final RecordDialogMode initialMode;

  const SalesPersonRecordDialog({
    super.key,
    required this.salesPerson,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    SalesPersonModel person, {
    required SalesPeopleCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<SalesPeopleCubit>.value(
        value: cubit,
        child: SalesPersonRecordDialog(
          salesPerson: person,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<SalesPersonRecordDialog> createState() =>
      _SalesPersonRecordDialogState();
}

class _SalesPersonRecordDialogState extends State<SalesPersonRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;
  late final TextEditingController _roleController;
  late final TextEditingController _createdByController;
  late final TextEditingController _createdAtController;

  late RecordDialogMode _mode;
  late CityModel? _selectedCity;
  bool _isSubmitting = false;
  String? _cityError;

  SalesPersonModel get _person => widget.salesPerson;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _nameController = TextEditingController(text: _person.name);
    _emailController = TextEditingController(text: _person.email);
    _phoneController = TextEditingController(text: _person.phoneNumber);
    _roleController = TextEditingController(
      text: RoleFormatter.label(_person.role),
    );
    _createdByController = TextEditingController(text: _person.createdByName);
    _createdAtController = TextEditingController(
      text: DateFormatter.label(_person.createdAt),
    );
    _selectedCity =
        MetadataService.instance.cityById(_person.cityId) ?? _person.city;
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
    _nameController.text = _person.name;
    _emailController.text = _person.email;
    _phoneController.text = _person.phoneNumber;
    _selectedCity =
        MetadataService.instance.cityById(_person.cityId) ?? _person.city;
    setState(() {
      _cityError = null;
      _mode = RecordDialogMode.view;
    });
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCityValid = _selectedCity != null;

    setState(
      () =>
          _cityError = isCityValid ? null : AppStrings.VALIDATION_CITY_REQUIRED,
    );

    if (!isFormValid || !isCityValid) return;

    setState(() => _isSubmitting = true);

    final SalesPeopleCubit cubit = context.read<SalesPeopleCubit>();
    final String email = _emailController.text.trim();

    final bool succeeded = await cubit.updateSalesPerson(
      id: _person.id,
      name: _nameController.text.trim(),
      phoneNumber: _phoneController.text.trim(),
      cityId: _selectedCity!.id,
      email: email.isEmpty ? null : email,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.SALES_PERSON_UPDATED_TITLE);
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
      icon: Icons.groups_outlined,
      title: AppStrings.SALES_PERSON_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.SALES_PERSON_EDIT_HINT
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
          provisioningUri: _person.provisioningUri,
          phoneNumber: _person.phoneNumber,
          subjectName: _person.name,
          isStacked: true,
        ),
      ),
    );
  }

  void _notifyViewMode({bool isLocked = false}) {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: isLocked
          ? AppStrings.VIEW_MODE_LOCKED_TOAST_BODY
          : AppStrings.VIEW_MODE_TOAST_BODY,
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
          left: CityPickerField(
            value: _selectedCity,
            enabled: canEdit,
            errorText: _cityError,
            onBlockedTap: _notifyViewMode,
            onSelected: (city) => setState(() {
              _selectedCity = city;
              _cityError = null;
            }),
          ),
          right: RecordField(
            controller: _createdByController,
            label: AppStrings.DETAIL_FIELD_CREATED_BY,
            isEditable: canEdit,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
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
