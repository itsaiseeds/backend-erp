import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/entry_rail_panel.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/client_address_model.dart';
import '../../data/models/client_contact_model.dart';
import '../../data/models/client_model.dart';
import '../../data/models/client_status.dart';
import '../../data/models/transport_agency_model.dart';
import '../bloc/clients_cubit.dart';
import 'client_form_steps.dart';

class ClientRecordDialog extends StatefulWidget {
  final ClientsCubit cubit;
  final ClientModel client;
  final RecordDialogMode initialMode;

  const ClientRecordDialog({
    super.key,
    required this.cubit,
    required this.client,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context, {
    required ClientsCubit cubit,
    required ClientModel client,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ClientRecordDialog(
        cubit: cubit,
        client: client,
        initialMode: initialMode,
      ),
    );
  }

  @override
  State<ClientRecordDialog> createState() => _ClientRecordDialogState();
}

class _ClientRecordDialogState extends State<ClientRecordDialog> {
  static const int _phoneLength = 10;
  static const int _gstLength = 15;

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _phoneController;
  late final TextEditingController _gstController;
  late final TextEditingController _createdByController;

  late List<ClientAddressModel> _addresses;
  late List<ClientContactModel> _contacts;
  late List<TransportAgencyModel> _agencies;

  late RecordDialogMode _mode;
  ClientFormStep _step = ClientFormStep.details;
  bool _isSubmitting = false;
  int _expandedAddress = -1;
  int _expandedContact = -1;
  int _expandedAgency = -1;

  ClientModel get _client => widget.client;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  bool get _isLastStep => _step == ClientFormStep.transport;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _nameController = TextEditingController(text: _client.companyName);
    _phoneController = TextEditingController(text: _client.companyPhone);
    _gstController = TextEditingController(text: _client.gstNumber);
    _createdByController = TextEditingController(text: _client.createdBy);
    _resetLists();
  }

  void _resetLists() {
    _addresses = List<ClientAddressModel>.from(_client.addresses);
    _contacts = List<ClientContactModel>.from(_client.contacts);
    _agencies = List<TransportAgencyModel>.from(_client.transportAgencies);

    if (_addresses.isEmpty) _addresses = [const ClientAddressModel()];
    if (_contacts.isEmpty) _contacts = [const ClientContactModel()];
    if (_agencies.isEmpty) _agencies = [const TransportAgencyModel()];
  }

  @override
  void dispose() {
    _nameController.dispose();
    _phoneController.dispose();
    _gstController.dispose();
    _createdByController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _nameController.text = _client.companyName;
    _phoneController.text = _client.companyPhone;
    _gstController.text = _client.gstNumber;
    setState(() {
      _resetLists();
      _expandedAddress = -1;
      _expandedContact = -1;
      _expandedAgency = -1;
      _mode = RecordDialogMode.view;
    });
  }

  void _next() {
    if (_isEditing && !_validateCurrentStep()) return;
    setState(() => _step = ClientFormStep.values[_step.index + 1]);
  }

  void _back() =>
      setState(() => _step = ClientFormStep.values[_step.index - 1]);

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

  void _showError(String message) => ToastUtils.showError(
    context,
    AppStrings.LOGIN_FAILED_TITLE,
    description: message,
  );

  Future<void> _submit() async {
    if (!_validateCurrentStep()) return;

    setState(() => _isSubmitting = true);

    final ClientModel updated = _client.copyWith(
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

  bool get _isFirstStep => _step == ClientFormStep.details;

  String get _stepCaption {
    final int position = _step.index + 1;
    final int total = ClientFormStep.values.length;
    return '${_client.companyName} · '
        '${AppStrings.CLIENT_STEP_PROGRESS} $position/$total · '
        '${_step.label}';
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.storefront_outlined,
      title: AppStrings.CLIENT_DETAILS_TITLE,
      subtitle: _stepCaption,
      mode: _mode,
      body: _buildBody(),
      isBodyFlush: true,
      badge: AppBadge(
        label: ClientStatusX.labelOf(_client.status),
        variant: _client.status == ClientStatus.verified
            ? AppBadgeVariant.success
            : AppBadgeVariant.warning,
      ),
      onEdit: _enterEditMode,
      showFooterInViewMode: true,
      onCancelEdit: _isFirstStep ? _cancelEdit : _back,
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      isCancelEnabled: _isEditing || !_isFirstStep,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep ? (_isEditing ? _submit : null) : _next),
      submitLabel: _isLastStep ? AppStrings.SAVE : AppStrings.STEP_NEXT,
      isSubmitting: _isSubmitting,
    );
  }

  Widget _buildBody() {
    if (_isFirstStep) {
      return Align(
        alignment: Alignment.topLeft,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: _buildStepBody(),
        ),
      );
    }

    return _buildStepBody();
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
          RecordFieldRow(
            left: RecordField(
              controller: _nameController,
              label: AppStrings.COLUMN_COMPANY_NAME,
              hint: AppStrings.CLIENT_COMPANY_NAME_HINT,
              isEditable: _canEdit,
              validator: FormValidators.requiredField,
            ),
            right: RecordField(
              controller: _phoneController,
              label: AppStrings.COLUMN_COMPANY_PHONE,
              keyboardType: TextInputType.phone,
              isEditable: _canEdit,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(_phoneLength),
              ],
              validator: FormValidators.phoneNumber,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          RecordFieldRow(
            left: RecordField(
              controller: _gstController,
              label: AppStrings.COLUMN_GST_NUMBER,
              hint: AppStrings.CLIENT_GST_HINT,
              isEditable: _canEdit,
              inputFormatters: [
                LengthLimitingTextInputFormatter(_gstLength),
                _UpperCaseFormatter(),
              ],
              validator: _validateGst,
            ),
            right: RecordField(
              controller: _createdByController,
              label: AppStrings.CLIENT_CREATED_BY_LABEL,
              isEditable: _canEdit,
              isLocked: true,
            ),
          ),
        ],
      ),
    );
  }

  String _addressTitle(ClientAddressModel address, int index) {
    final String label = address.label.trim();
    if (label.isNotEmpty) return label;
    final String city = address.cityName.trim();
    if (city.isNotEmpty) return city;
    return '${AppStrings.CLIENT_STEP_ADDRESSES} ${index + 1}';
  }

  Widget _buildAddresses() {
    final int selected = _selectedIndexFor(_addresses.length, _expandedAddress);

    return EntryRailPanel(
      hint: AppStrings.CLIENT_RAIL_ADDRESSES_HINT,
      addLabel: AppStrings.CLIENT_ADD_ADDRESS,
      primaryLabel: AppStrings.CLIENT_PRIMARY_BADGE,
      selectedIndex: selected,
      onSelected: (index) => setState(() => _expandedAddress = index),
      onAdd: _canEdit ? _addEntry : null,
      onRemove: _canEdit && _addresses.length > 1
          ? (index) => setState(() {
              _addresses.removeAt(index);
              _expandedAddress = 0;
            })
          : null,
      entries: [
        for (int index = 0; index < _addresses.length; index++)
          EntryRailItem(
            title: _addressTitle(_addresses[index], index),
            isPrimary: _addresses[index].isPrimary,
          ),
      ],
      detail: AddressStepCard(
        key: ValueKey<int>(selected),
        isBare: true,
        address: _addresses[selected],
        index: selected,
        canRemove: false,
        enabled: _canEdit,
        onChanged: (value) => setState(() => _addresses[selected] = value),
        onRemove: () {},
        onMakePrimary: () => setState(() {
          _addresses = [
            for (int i = 0; i < _addresses.length; i++)
              _addresses[i].copyWith(isPrimary: i == selected),
          ];
        }),
      ),
    );
  }

  Widget _buildContacts() {
    final int selected = _selectedIndexFor(_contacts.length, _expandedContact);

    return EntryRailPanel(
      hint: AppStrings.CLIENT_RAIL_CONTACTS_HINT,
      addLabel: AppStrings.CLIENT_ADD_CONTACT,
      primaryLabel: AppStrings.CLIENT_PRIMARY_BADGE,
      selectedIndex: selected,
      onSelected: (index) => setState(() => _expandedContact = index),
      onAdd: _canEdit ? _addEntry : null,
      onRemove: _canEdit && _contacts.length > 1
          ? (index) => setState(() {
              _contacts.removeAt(index);
              _expandedContact = 0;
            })
          : null,
      entries: [
        for (int index = 0; index < _contacts.length; index++)
          EntryRailItem(
            title: _contacts[index].name.trim().isEmpty
                ? '${AppStrings.CLIENT_STEP_CONTACTS} ${index + 1}'
                : _contacts[index].name.trim(),
            isPrimary: _contacts[index].isPrimary,
          ),
      ],
      detail: ContactStepCard(
        key: ValueKey<int>(selected),
        isBare: true,
        contact: _contacts[selected],
        index: selected,
        canRemove: false,
        enabled: _canEdit,
        onChanged: (value) => setState(() => _contacts[selected] = value),
        onRemove: () {},
        onMakePrimary: () => setState(() {
          _contacts = [
            for (int i = 0; i < _contacts.length; i++)
              ClientContactModel(
                name: _contacts[i].name,
                phoneNumber: _contacts[i].phoneNumber,
                role: _contacts[i].role,
                isPrimary: i == selected,
              ),
          ];
        }),
      ),
    );
  }

  Widget _buildTransport() {
    final int selected = _selectedIndexFor(_agencies.length, _expandedAgency);

    return EntryRailPanel(
      hint: AppStrings.CLIENT_RAIL_TRANSPORT_HINT,
      addLabel: AppStrings.CLIENT_ADD_TRANSPORT,
      primaryLabel: AppStrings.CLIENT_PRIMARY_BADGE,
      selectedIndex: selected,
      onSelected: (index) => setState(() => _expandedAgency = index),
      onAdd: _canEdit ? _addEntry : null,
      onRemove: _canEdit && _agencies.length > 1
          ? (index) => setState(() {
              _agencies.removeAt(index);
              _expandedAgency = 0;
            })
          : null,
      entries: [
        for (int index = 0; index < _agencies.length; index++)
          EntryRailItem(
            title: _agencies[index].name.trim().isEmpty
                ? '${AppStrings.CLIENT_STEP_TRANSPORT} ${index + 1}'
                : _agencies[index].name.trim(),
            isPrimary: _agencies[index].isPrimary,
          ),
      ],
      detail: TransportStepCard(
        key: ValueKey<int>(selected),
        isBare: true,
        agency: _agencies[selected],
        index: selected,
        canRemove: false,
        enabled: _canEdit,
        onChanged: (value) => setState(() => _agencies[selected] = value),
        onRemove: () {},
        onMakePrimary: () => setState(() {
          _agencies = [
            for (int i = 0; i < _agencies.length; i++)
              TransportAgencyModel(
                name: _agencies[i].name,
                isPrimary: i == selected,
              ),
          ];
        }),
      ),
    );
  }

  int _selectedIndexFor(int length, int candidate) {
    if (length == 0) return 0;
    if (candidate < 0 || candidate >= length) return 0;
    return candidate;
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
