import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/party_model.dart';
import '../bloc/parties_cubit.dart';

class PartyRecordDialog extends StatefulWidget {
  final PartyModel party;
  final RecordDialogMode initialMode;

  const PartyRecordDialog({
    super.key,
    required this.party,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    PartyModel party, {
    required PartiesCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<PartiesCubit>.value(
        value: cubit,
        child: PartyRecordDialog(party: party, initialMode: initialMode),
      ),
    );
  }

  @override
  State<PartyRecordDialog> createState() => _PartyRecordDialogState();
}

class _PartyRecordDialogState extends State<PartyRecordDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _contactController;

  late RecordDialogMode _mode;
  late CityModel? _selectedCity;
  bool _isSubmitting = false;
  String? _cityError;

  PartyModel get _party => widget.party;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _nameController = TextEditingController(text: _party.name);
    _contactController = TextEditingController(text: _party.contactNumber);
    _selectedCity = _resolveCity();
  }

  CityModel? _resolveCity() =>
      MetadataService.instance.cityById(_party.cityId) ?? _party.city;

  @override
  void dispose() {
    _nameController.dispose();
    _contactController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _nameController.text = _party.name;
    _contactController.text = _party.contactNumber;

    setState(() {
      _selectedCity = _resolveCity();
      _cityError = null;
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
    final bool isCityValid = _selectedCity != null;

    setState(
      () =>
          _cityError = isCityValid ? null : AppStrings.VALIDATION_CITY_REQUIRED,
    );

    if (!isFormValid || !isCityValid) return;

    setState(() => _isSubmitting = true);

    final PartiesCubit cubit = context.read<PartiesCubit>();
    final String contact = _contactController.text.trim();

    final bool succeeded = await cubit.updateParty(
      id: _party.id,
      name: _nameController.text.trim(),
      cityId: _selectedCity!.id,
      contactNumber: contact.isEmpty ? null : contact,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.PARTY_UPDATED_TITLE);
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
      icon: Icons.handshake_outlined,
      title: AppStrings.PARTY_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.EDIT_PARTY_SUBTITLE
          : AppStrings.PARTY_DETAIL_SUBTITLE,
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
            label: AppStrings.COLUMN_PARTY_NAME,
            hint: AppStrings.FIELD_PARTY_NAME_HINT,
            isEditable: _canEdit,
            validator: FormValidators.requiredField,
          ),
          right: CityPickerField(
            value: _selectedCity,
            enabled: _canEdit,
            errorText: _cityError,
            onBlockedTap: _notifyViewMode,
            onSelected: (city) => setState(() {
              _selectedCity = city;
              _cityError = null;
            }),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _contactController,
            label: AppStrings.COLUMN_PARTY_CONTACT,
            hint: AppStrings.FIELD_PARTY_CONTACT_HINT,
            keyboardType: TextInputType.phone,
            isEditable: _canEdit,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(
                FormValidators.PHONE_NUMBER_LENGTH,
              ),
            ],
            validator: FormValidators.optionalPhoneNumber,
          ),
        ),
      ],
    );
  }
}
