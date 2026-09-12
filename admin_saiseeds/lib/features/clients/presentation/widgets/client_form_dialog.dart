import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../data/models/client_address_model.dart';
import '../../data/models/client_contact_model.dart';
import '../../data/models/client_model.dart';
import '../../data/models/transport_agency_model.dart';
import '../bloc/clients_cubit.dart';
import 'client_form_steps.dart';

class ClientFormDialog extends StatefulWidget {
  final ClientsCubit cubit;
  final ClientModel client;

  const ClientFormDialog({
    super.key,
    required this.cubit,
    required this.client,
  });

  static Future<void> show(
    BuildContext context, {
    required ClientsCubit cubit,
    required ClientModel client,
  }) {
    return showDialog<void>(
      context: context,
      builder: (_) => ClientFormDialog(cubit: cubit, client: client),
    );
  }

  @override
  State<ClientFormDialog> createState() => _ClientFormDialogState();
}

class _ClientFormDialogState extends State<ClientFormDialog> {
  static const int _phoneLength = 10;
  static const int _gstLength = 15;

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _gstController;

  late List<ClientAddressModel> _addresses;
  late List<ClientContactModel> _contacts;
  late List<TransportAgencyModel> _agencies;

  ClientFormStep _step = ClientFormStep.details;
  bool _isSubmitting = false;
  int _expandedAddress = -1;
  int _expandedContact = -1;
  int _expandedAgency = -1;

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController(text: widget.client.companyName);
    _phoneController = TextEditingController(text: widget.client.companyPhone);
    _gstController = TextEditingController(text: widget.client.gstNumber);

    _addresses = List<ClientAddressModel>.from(widget.client.addresses);
    _contacts = List<ClientContactModel>.from(widget.client.contacts);
    _agencies = List<TransportAgencyModel>.from(widget.client.transportAgencies);

    if (_addresses.isEmpty) _addresses = [const ClientAddressModel()];
    if (_contacts.isEmpty) _contacts = [const ClientContactModel()];
    if (_agencies.isEmpty) _agencies = [const TransportAgencyModel()];
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _gstController.dispose();
    super.dispose();
  }

  bool get _isLastStep => _step == ClientFormStep.transport;

  void _goTo(ClientFormStep step) {
    if (step.index > _step.index && !_validateCurrentStep()) return;
    setState(() => _step = step);
  }

  void _next() {
    if (!_validateCurrentStep()) return;
    setState(() => _step = ClientFormStep.values[_step.index + 1]);
  }

  void _back() {
    setState(() => _step = ClientFormStep.values[_step.index - 1]);
  }

  bool _validateCurrentStep() {
    if (_step == ClientFormStep.details) {
      return _formKey.currentState?.validate() ?? false;
    }

    if (_step == ClientFormStep.addresses) {
      if (_addresses.any((a) => a.cityId == 0)) {
        _showError(AppStrings.VALIDATION_CITY_REQUIRED);
        return false;
      }
      if (_addresses.any((a) => a.line1.trim().isEmpty)) {
        _showError(AppStrings.VALIDATION_NAME_REQUIRED);
        return false;
      }
      return _validatePrimary(_addresses.map((a) => a.isPrimary));
    }

    if (_step == ClientFormStep.contacts) {
      if (_contacts.any((c) => c.name.trim().isEmpty)) {
        _showError(AppStrings.VALIDATION_NAME_REQUIRED);
        return false;
      }
      return _validatePrimary(_contacts.map((c) => c.isPrimary));
    }

    if (_agencies.any((a) => a.name.trim().isEmpty)) {
      _showError(AppStrings.VALIDATION_NAME_REQUIRED);
      return false;
    }
    return _validatePrimary(_agencies.map((a) => a.isPrimary));
  }

  bool _validatePrimary(Iterable<bool> flags) {
    if (flags.where((isPrimary) => isPrimary).length == 1) return true;
    _showError(AppStrings.VALIDATION_ONE_PRIMARY);
    return false;
  }

  void _showError(String message) =>
      ToastUtils.showError(context, AppStrings.LOGIN_FAILED_TITLE,
          description: message);

  Future<void> _submit() async {
    if (!_validateCurrentStep()) return;

    setState(() => _isSubmitting = true);

    final ClientModel updated = widget.client.copyWith(
      companyName: _nameController.text.trim(),
      companyPhone: _phoneController.text.trim(),
      gstNumber: _gstController.text.trim().toUpperCase(),
      addresses: _addresses,
      contacts: _contacts,
      transportAgencies: _agencies,
    );

    final bool succeeded = await widget.cubit.updateClient(updated);
    if (!mounted) return;

    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.CLIENT_UPDATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      widget.cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  String? _validateGst(String? value) {
    final String trimmed = value?.trim() ?? '';
    if (trimmed.isEmpty) return AppStrings.VALIDATION_GST_REQUIRED;
    if (trimmed.length != _gstLength) return AppStrings.VALIDATION_GST_INVALID;
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.storefront_outlined,
      title: AppStrings.CLIENT_EDIT_TITLE,
      subtitle: widget.client.companyName,
      submitLabel: _isLastStep ? AppStrings.SAVE : AppStrings.STEP_NEXT,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : (_isLastStep ? _submit : _next),
      leadingAction: _step == ClientFormStep.details
          ? null
          : SecondaryButton(
              label: AppStrings.STEP_BACK,
              onPressed: _isSubmitting ? null : _back,
            ),
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          ClientStepIndicator(
            current: _step,
            onStepTapped: _isSubmitting ? null : _goTo,
          ),
          const SizedBox(height: AppSpacing.lg),
          _buildStepBody(),
          if (_step != ClientFormStep.details) ...[
            const SizedBox(height: AppSpacing.sm),
            SecondaryButton(
              label: _addLabel,
              icon: Icons.add_rounded,
              onPressed: _isSubmitting ? null : _addEntry,
            ),
          ],
        ],
      ),
    );
  }

  String get _addLabel {
    switch (_step) {
      case ClientFormStep.addresses:
        return AppStrings.CLIENT_ADD_ADDRESS;
      case ClientFormStep.contacts:
        return AppStrings.CLIENT_ADD_CONTACT;
      case ClientFormStep.transport:
        return AppStrings.CLIENT_ADD_TRANSPORT;
      case ClientFormStep.details:
        return '';
    }
  }

  void _addEntry() {
    setState(() {
      switch (_step) {
        case ClientFormStep.addresses:
          _addresses = [..._addresses, const ClientAddressModel()];
          _expandedAddress = _addresses.length - 1;
        case ClientFormStep.contacts:
          _contacts = [..._contacts, const ClientContactModel()];
          _expandedContact = _contacts.length - 1;
        case ClientFormStep.transport:
          _agencies = [..._agencies, const TransportAgencyModel()];
          _expandedAgency = _agencies.length - 1;
        case ClientFormStep.details:
          break;
      }
    });
  }

  Widget _buildStepBody() {
    switch (_step) {
      case ClientFormStep.details:
        return _buildDetails();
      case ClientFormStep.addresses:
        return _buildAddresses();
      case ClientFormStep.contacts:
        return _buildContacts();
      case ClientFormStep.transport:
        return _buildTransport();
    }
  }

  Widget _buildDetails() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppTextField(
            controller: _nameController,
            label: AppStrings.COLUMN_COMPANY_NAME,
            hint: AppStrings.CLIENT_COMPANY_NAME_HINT,
            validator: FormValidators.requiredField,
            enabled: !_isSubmitting,
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            controller: _phoneController,
            label: AppStrings.COLUMN_COMPANY_PHONE,
            prefixText: AppStrings.PHONE_COUNTRY_CODE_IN,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(_phoneLength),
            ],
            validator: FormValidators.phoneNumber,
            enabled: !_isSubmitting,
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            controller: _gstController,
            label: AppStrings.COLUMN_GST_NUMBER,
            hint: AppStrings.CLIENT_GST_HINT,
            inputFormatters: [
              LengthLimitingTextInputFormatter(_gstLength),
              _UpperCaseFormatter(),
            ],
            validator: _validateGst,
            enabled: !_isSubmitting,
          ),
        ],
      ),
    );
  }

  Widget _buildAddresses() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int index = 0; index < _addresses.length; index++)
          AddressStepCard(
            key: ValueKey<int>(index),
            initiallyExpanded: _expandedAddress == index,
            address: _addresses[index],
            index: index,
            canRemove: _addresses.length > 1,
            enabled: !_isSubmitting,
            onChanged: (value) => setState(() => _addresses[index] = value),
            onRemove: () => setState(() => _addresses.removeAt(index)),
            onMakePrimary: () => setState(() {
              _addresses = [
                for (int i = 0; i < _addresses.length; i++)
                  _addresses[i].copyWith(isPrimary: i == index),
              ];
            }),
          ),
      ],
    );
  }

  Widget _buildContacts() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int index = 0; index < _contacts.length; index++)
          ContactStepCard(
            key: ValueKey<int>(index),
            initiallyExpanded: _expandedContact == index,
            contact: _contacts[index],
            index: index,
            canRemove: _contacts.length > 1,
            enabled: !_isSubmitting,
            onChanged: (value) => setState(() => _contacts[index] = value),
            onRemove: () => setState(() => _contacts.removeAt(index)),
            onMakePrimary: () => setState(() {
              _contacts = [
                for (int i = 0; i < _contacts.length; i++)
                  ClientContactModel(
                    name: _contacts[i].name,
                    phoneNumber: _contacts[i].phoneNumber,
                    role: _contacts[i].role,
                    isPrimary: i == index,
                  ),
              ];
            }),
          ),
      ],
    );
  }

  Widget _buildTransport() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int index = 0; index < _agencies.length; index++)
          TransportStepCard(
            key: ValueKey<int>(index),
            initiallyExpanded: _expandedAgency == index,
            agency: _agencies[index],
            index: index,
            canRemove: _agencies.length > 1,
            enabled: !_isSubmitting,
            onChanged: (value) => setState(() => _agencies[index] = value),
            onRemove: () => setState(() => _agencies.removeAt(index)),
            onMakePrimary: () => setState(() {
              _agencies = [
                for (int i = 0; i < _agencies.length; i++)
                  TransportAgencyModel(
                    name: _agencies[i].name,
                    isPrimary: i == index,
                  ),
              ];
            }),
          ),
      ],
    );
  }
}

class _UpperCaseFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    return TextEditingValue(
      text: newValue.text.toUpperCase(),
      selection: newValue.selection,
    );
  }
}
