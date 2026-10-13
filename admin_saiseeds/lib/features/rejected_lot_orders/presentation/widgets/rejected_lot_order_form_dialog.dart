import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/parties_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/party_picker_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/client_address_model.dart';
import '../../../clients/data/models/client_model.dart';
import '../../../clients/data/models/client_status.dart';
import '../../../orders/presentation/widgets/delivery_to_field.dart';
import '../../../parties/data/models/party_model.dart';
import '../../data/models/rejected_farmer_model.dart';
import '../../data/models/rejected_lot_model.dart';
import '../../data/rejected_lot_orders_repository.dart';
import '../bloc/rejected_lot_orders_cubit.dart';
import 'rejected_lot_destination_field.dart';
import 'rejected_lot_order_line_row.dart';
import 'rejected_lot_picker_dialog.dart';

/// Books a rejected-lot order over four steps: who it's for and the source
/// party/farmer, which of that farmer's rejected lots are being sold, the
/// shipment details, then a final summary. Booking this order kind is its
/// own dispatch -- there is no later confirm step.
class RejectedLotOrderFormDialog extends StatefulWidget {
  const RejectedLotOrderFormDialog({super.key});

  static final DateFormat isoDate = DateFormat('yyyy-MM-dd');

  static Future<void> show(
    BuildContext context, {
    required RejectedLotOrdersCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<RejectedLotOrdersCubit>.value(
        value: cubit,
        child: const RejectedLotOrderFormDialog(),
      ),
    );
  }

  @override
  State<RejectedLotOrderFormDialog> createState() =>
      _RejectedLotOrderFormDialogState();
}

class _RejectedLotOrderFormDialogState
    extends State<RejectedLotOrderFormDialog> {
  static const List<IconData> _ICONS = [
    Icons.storefront_outlined,
    Icons.inventory_2_outlined,
    Icons.local_shipping_outlined,
    Icons.fact_check_outlined,
  ];

  static const List<String> _STEPS = [
    AppStrings.REJECTED_LOT_ORDER_STEP_CLIENT,
    AppStrings.REJECTED_LOT_ORDER_STEP_SOURCE,
    AppStrings.REJECTED_LOT_ORDER_STEP_SHIPMENT,
    AppStrings.REJECTED_LOT_ORDER_STEP_SUMMARY,
  ];

  static const List<String> _CAPTIONS = [
    AppStrings.REJECTED_LOT_ORDER_STEP_CLIENT_CAPTION,
    AppStrings.REJECTED_LOT_ORDER_STEP_SOURCE_CAPTION,
    AppStrings.REJECTED_LOT_ORDER_STEP_SHIPMENT_CAPTION,
    AppStrings.REJECTED_LOT_ORDER_STEP_SUMMARY_CAPTION,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final GlobalKey<RejectedLotDestinationFieldState> _destinationKey =
      GlobalKey<RejectedLotDestinationFieldState>();
  final TextEditingController _commentsController = TextEditingController();
  final TextEditingController _hsnController = TextEditingController();
  final TextEditingController _vehicleController = TextEditingController();
  final TextEditingController _driverNameController = TextEditingController();
  final TextEditingController _driverNumberController = TextEditingController();

  int _stepIndex = 0;
  bool _isSubmitting = false;

  // Step 1 -- client, destination, and source party/farmer.
  List<ClientModel> _clients = [];
  ClientModel? _client;
  List<ClientAddressModel> _addresses = const [];
  ClientAddressModel? _address;
  bool _isLoadingClients = true;
  DeliveryToValue _deliveryTo = const DeliveryToValue.none();
  String? _clientError;
  String? _addressError;
  PartyModel? _party;
  List<RejectedFarmerModel> _farmers = const [];
  RejectedFarmerModel? _farmer;
  bool _isLoadingFarmers = false;
  String? _partyError;
  String? _farmerError;

  // Step 2 -- source lots.
  List<RejectedLotModel> _availableLots = const [];
  List<RejectedLotOrderLine> _lines = [];
  bool _isLoadingLots = false;
  String? _linesError;

  // Step 3 -- shipment.
  CityModel? _fromCity;
  DateTime? _expectedDelivery;
  String? _cityError;

  late final RejectedLotOrdersRepository _repository = RejectedLotOrdersRepository(
    apiClient: context.read<ApiClient>(),
  );

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  bool get _canEdit => !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _loadClients();
    _loadParties();
  }

  @override
  void dispose() {
    _commentsController.dispose();
    _hsnController.dispose();
    _vehicleController.dispose();
    _driverNameController.dispose();
    _driverNumberController.dispose();
    for (final RejectedLotOrderLine line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  Future<void> _loadParties() async {
    await PartiesService.instance.loadParties();
    if (mounted) setState(() {});
  }

  /// Only verified clients can be ordered for, same filter custom orders use.
  Future<void> _loadClients() async {
    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final result = await repository.fetchClients(
        queryParams: {
          'all': true,
          AppStrings.FILTER_BY_STATUS: ClientStatusX.VERIFIED,
        },
      );
      if (!mounted) return;
      setState(() {
        _clients = result.results;
        _isLoadingClients = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingClients = false);
    }
  }

  /// The client's primary address is picked silently -- the form never
  /// shows an address picker (the consignee only ever needs the client's
  /// name; showing its address alongside the real delivery destination, the
  /// farmer section below, read as confusing).
  Future<void> _loadAddresses(ClientModel client) async {
    setState(() {
      _addresses = const [];
      _address = null;
    });

    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final ClientModel full = await repository.fetchClient(client.publicId);
      if (!mounted || _client?.publicId != client.publicId) return;

      setState(() {
        _addresses = full.addresses;
        _address = _addresses.isEmpty ? null : _primaryOf(_addresses);
      });
    } catch (_) {
      // Leave _address null -- _validateClient's address check catches it.
    }
  }

  static ClientAddressModel _primaryOf(List<ClientAddressModel> addresses) {
    for (final ClientAddressModel address in addresses) {
      if (address.isPrimary) return address;
    }
    return addresses.first;
  }

  Future<void> _selectParty(PartyModel party) async {
    setState(() {
      _party = party;
      _partyError = null;
      _farmers = const [];
      _farmer = null;
      _availableLots = const [];
      _isLoadingFarmers = true;
    });

    final List<RejectedFarmerModel> farmers = await _repository.fetchFarmers(
      party.id,
    );
    if (!mounted || _party?.id != party.id) return;
    setState(() {
      _farmers = farmers;
      _isLoadingFarmers = false;
    });
  }

  Future<void> _selectFarmer(RejectedFarmerModel farmer) async {
    setState(() {
      _farmer = farmer;
      _farmerError = null;
      _availableLots = const [];
      _isLoadingLots = true;
    });

    final List<RejectedLotModel> lots = await _repository.fetchLots(
      _party!.id,
      farmer.farmerName,
    );
    if (!mounted || _farmer?.farmerName != farmer.farmerName) return;
    setState(() {
      _availableLots = lots.where((lot) => lot.hasStockLeft).toList();
      _isLoadingLots = false;
    });
  }

  Future<void> _addLot() async {
    final List<RejectedLotModel>? picked = await RejectedLotPickerDialog.show(
      context,
      lots: _availableLots
          .where(
            (lot) => !_lines.any(
              (line) => line.key == lot.inwardRawMaterialPublicId,
            ),
          )
          .toList(),
    );
    if (picked == null || picked.isEmpty || !mounted) return;

    setState(
      () => _lines = [
        ..._lines,
        for (final RejectedLotModel lot in picked) RejectedLotOrderLine(lot: lot),
      ],
    );
  }

  void _removeLine(int index) {
    setState(() {
      final List<RejectedLotOrderLine> next = [..._lines];
      next.removeAt(index).dispose();
      _lines = next;
    });
  }

  num get _liveTotalAmount =>
      _lines.fold<num>(0, (sum, line) => sum + line.lineTotal);

  num get _liveTotalKg => _lines.fold<num>(
    0,
    (sum, line) => sum + (num.tryParse(line.quantity.text.trim()) ?? 0),
  );

  /// `"<farmer name> (<party name>)"` -- what [RejectedLotDestinationField]
  /// folds into `booked_for.party_name`. Blank until both pickers are set,
  /// which also doubles as this step's "is the source chosen" check.
  String get _bookedForPartyName {
    if (_farmer == null || _party == null) return '';
    return '${_farmer!.farmerName} (${_party!.name})';
  }

  bool _validateClient() {
    final bool clientValid = _client != null;
    final bool addressValid = _address != null;
    final bool partyValid = _party != null;
    final bool farmerValid = _farmer != null;
    // _destinationKey's widget only exists while step 0 is on screen, so its
    // currentState is null once the user has moved past it (step 2, 3, the
    // final submit...). The already-committed _deliveryTo -- kept in sync by
    // the field's own onChanged while it was mounted -- is what a later step
    // has to check instead; re-running the live validator here would always
    // read null and wrongly bounce every submit back to step 1.
    final bool destinationValid = _stepIndex == 0
        ? (_destinationKey.currentState?.validate() ?? false)
        : _deliveryTo.isSet;

    setState(() {
      _clientError = clientValid ? null : AppStrings.VALIDATION_CLIENT_REQUIRED;
      _addressError = addressValid
          ? null
          : AppStrings.VALIDATION_ADDRESS_REQUIRED;
      _partyError = partyValid ? null : AppStrings.VALIDATION_PARTY_REQUIRED;
      _farmerError = farmerValid ? null : AppStrings.VALIDATION_FARMER_REQUIRED;
    });

    return clientValid &&
        addressValid &&
        partyValid &&
        farmerValid &&
        destinationValid;
  }

  bool _validateLines() {
    final bool linesValid = _lines.isNotEmpty && _lines.every((l) => l.isValid);

    setState(
      () => _linesError = linesValid
          ? null
          : AppStrings.REJECTED_LOT_ORDER_LOT_INVALID,
    );

    return linesValid;
  }

  bool _validateShipment() {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCityValid = _fromCity != null;

    setState(
      () => _cityError = isCityValid
          ? null
          : AppStrings.VALIDATION_FROM_CITY_REQUIRED,
    );

    return isFormValid && isCityValid;
  }

  void _goTo(int index) {
    if (index > _stepIndex) {
      if (_stepIndex == 0 && !_validateClient()) return;
      if (_stepIndex == 1 && !_validateLines()) return;
      if (_stepIndex == 2 && !_validateShipment()) return;
    }
    setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));
  }

  Future<void> _submit() async {
    if (!_validateClient()) {
      setState(() => _stepIndex = 0);
      return;
    }
    if (!_validateLines()) {
      setState(() => _stepIndex = 1);
      return;
    }
    if (!_validateShipment()) {
      setState(() => _stepIndex = 2);
      return;
    }

    setState(() => _isSubmitting = true);
    final RejectedLotOrdersCubit cubit = context.read<RejectedLotOrdersCubit>();

    final bool succeeded = await cubit.createRejectedOrder({
      'client_public_id': _client!.publicId,
      'client_address_id': _address!.id,
      'special_comments': _commentsController.text.trim(),
      if (_expectedDelivery != null)
        'expected_delivery_date': RejectedLotOrderFormDialog.isoDate.format(
          _expectedDelivery!,
        ),
      'items': [for (final RejectedLotOrderLine line in _lines) line.toJson()],
      if (_deliveryTo.isSet) 'booked_for': _deliveryTo.toRequestValue(),
      'hsn_code': _hsnController.text.trim(),
      'from_city_id': _fromCity!.id,
      'driver_name': _driverNameController.text.trim(),
      'driver_number': _driverNumberController.text.trim(),
      'vehicle_number': _vehicleController.text.trim(),
    });

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.REJECTED_LOT_ORDER_CREATED);
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
      icon: Icons.remove_shopping_cart_outlined,
      title: AppStrings.REJECTED_LOT_ORDER_ADD,
      subtitle:
          '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
          '${AppStrings.LABEL_SEPARATOR} ${_CAPTIONS[_stepIndex]}',
      mode: RecordDialogMode.edit,
      isSubmitting: _isSubmitting,
      extraHeight: AppSizes.recordDialogRoomyBump * 2,
      onCancelEdit: _isFirstStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep ? _submit : () => _goTo(_stepIndex + 1)),
      submitLabel: _isLastStep ? AppStrings.CREATE : AppStrings.STEP_NEXT,
      body: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            SectionTitle(
              title: _STEPS[_stepIndex],
              icon: _ICONS[_stepIndex],
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildStep(),
          ],
        ),
      ),
    );
  }

  Widget _buildStep() {
    switch (_stepIndex) {
      case 1:
        return _buildSource();
      case 2:
        return _buildShipment();
      case 3:
        return _buildSummary();
      default:
        return _buildClient();
    }
  }

  Widget _buildClient() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SearchableField<ClientModel>(
          label: AppStrings.COLUMN_ORDER_CLIENT,
          hintText: _isLoadingClients
              ? AppStrings.LOADING
              : AppStrings.FIELD_CLIENT_HINT,
          value: _client,
          items: _clients,
          itemToString: (client) => client.companyName,
          isSame: (a, b) => a.publicId == b.publicId,
          enabled: _canEdit && !_isLoadingClients,
          errorText: _clientError,
          onSelected: (client) {
            setState(() {
              _client = client;
              _clientError = null;
              _addressError = null;
            });
            _loadAddresses(client);
          },
        ),
        if (_addressError != null) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            _addressError!,
            style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        SectionTitle(
          title: AppStrings.DELIVERY_TO_SECTION,
          icon: Icons.alt_route_outlined,
        ),
        const SizedBox(height: AppSpacing.smd),
        PartyPickerField(
          value: _party,
          parties: PartiesService.instance.rawMaterialParties,
          enabled: _canEdit,
          errorText: _partyError,
          onSelected: _selectParty,
        ),
        const SizedBox(height: AppSpacing.md),
        SearchableField<RejectedFarmerModel>(
          label: AppStrings.FIELD_FARMER,
          hintText: _isLoadingFarmers
              ? AppStrings.LOADING
              : AppStrings.FIELD_FARMER_HINT,
          value: _farmer,
          items: _farmers,
          itemToString: (farmer) => farmer.farmerName,
          isSame: (a, b) => a.farmerName == b.farmerName,
          enabled: _canEdit && !_isLoadingFarmers && _party != null,
          errorText: _farmerError,
          emptyHint: AppStrings.FARMERS_UNAVAILABLE,
          onSelected: _selectFarmer,
        ),
        const SizedBox(height: AppSpacing.md),
        RejectedLotDestinationField(
          key: _destinationKey,
          partyName: _bookedForPartyName,
          initial: _deliveryTo,
          enabled: _canEdit,
          onChanged: (value) => setState(() => _deliveryTo = value),
        ),
      ],
    );
  }

  Widget _buildSource() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_lines.isEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              AppStrings.REJECTED_LOT_ORDER_NO_LOTS,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
        for (int index = 0; index < _lines.length; index++) ...[
          if (index > 0) ...[
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.sm),
          ],
          RejectedLotOrderLineRow(
            line: _lines[index],
            onRemove: _canEdit ? () => _removeLine(index) : null,
            onChanged: () => setState(() {}),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        if (_isLoadingLots)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else
          SecondaryButton(
            label: AppStrings.REJECTED_LOT_ORDER_ADD_LOT,
            icon: Icons.add_rounded,
            onPressed: _canEdit && _availableLots.isNotEmpty ? _addLot : null,
          ),
        if (_linesError != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            _linesError!,
            style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Expanded(
              child: Text(
                AppStrings.COLUMN_ORDER_AMOUNT,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ),
            Text(
              CurrencyFormatter.rupees(_liveTotalAmount),
              style: AppTypography.labelStrong,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildShipment() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: CityPickerField(
            value: _fromCity,
            fieldLabel: AppStrings.FIELD_FROM_CITY,
            enabled: _canEdit,
            errorText: _cityError,
            onSelected: (city) => setState(() {
              _fromCity = city;
              _cityError = null;
            }),
          ),
          right: AppTextField(
            controller: _vehicleController,
            label: AppStrings.FIELD_VEHICLE_NUMBER,
            hint: AppStrings.FIELD_VEHICLE_NUMBER_HINT,
            enabled: _canEdit,
            validator: FormValidators.requiredField,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: AppTextField(
            controller: _driverNameController,
            label: AppStrings.FIELD_DRIVER_NAME,
            hint: AppStrings.FIELD_DRIVER_NAME_HINT,
            enabled: _canEdit,
            validator: FormValidators.requiredField,
          ),
          right: AppTextField(
            controller: _driverNumberController,
            label: AppStrings.FIELD_DRIVER_NUMBER,
            hint: AppStrings.LOGIN_PHONE_HINT,
            keyboardType: TextInputType.phone,
            enabled: _canEdit,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(
                FormValidators.PHONE_NUMBER_LENGTH,
              ),
            ],
            validator: FormValidators.phoneNumber,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: AppTextField(
            controller: _hsnController,
            label: AppStrings.FIELD_HSN_CODE,
            hint: AppStrings.FIELD_HSN_CODE_HINT,
            enabled: _canEdit,
          ),
          right: SingleDateField(
            label: AppStrings.FIELD_EXPECTED_DELIVERY,
            value: _expectedDelivery,
            enabled: _canEdit,
            onChanged: (date) => setState(() => _expectedDelivery = date),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextField(
          controller: _commentsController,
          label: AppStrings.FIELD_SPECIAL_COMMENTS,
          hint: AppStrings.FIELD_SPECIAL_COMMENTS_HINT,
          enabled: _canEdit,
        ),
      ],
    );
  }

  Widget _buildSummary() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _SummaryRow(label: AppStrings.COLUMN_ORDER_CLIENT, value: _client?.companyName ?? ''),
        _SummaryRow(
          label: AppStrings.FIELD_FARMER,
          value: _deliveryTo.partyName,
        ),
        const SizedBox(height: AppSpacing.md),
        SectionTitle(
          title: AppStrings.REJECTED_LOT_ORDER_SUMMARY_LOTS,
          icon: Icons.inventory_2_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.sm),
        for (final RejectedLotOrderLine line in _lines)
          _SummaryRow(
            label: '${line.lot.productName} - ${line.lot.lotNo}',
            value:
                '${line.quantity.text.trim()} kg @ '
                '${CurrencyFormatter.rupees(num.tryParse(line.price.text.trim()) ?? 0)}',
          ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: Text(
                AppStrings.COLUMN_ORDER_AMOUNT,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ),
            Text(
              '${CurrencyFormatter.rupees(_liveTotalAmount)} '
              '(${_liveTotalKg.toStringAsFixed(3)} kg)',
              style: AppTypography.labelStrong,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        SectionTitle(
          title: AppStrings.REJECTED_LOT_ORDER_STEP_SHIPMENT,
          icon: Icons.local_shipping_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.sm),
        _SummaryRow(label: AppStrings.FIELD_FROM_CITY, value: _fromCity?.name ?? ''),
        _SummaryRow(
          label: AppStrings.FIELD_VEHICLE_NUMBER,
          value: _vehicleController.text.trim(),
        ),
        _SummaryRow(
          label: AppStrings.FIELD_DRIVER_NAME,
          value: _driverNameController.text.trim(),
        ),
        _SummaryRow(
          label: AppStrings.FIELD_DRIVER_NUMBER,
          value: _driverNumberController.text.trim(),
        ),
      ],
    );
  }
}

class _SummaryRow extends StatelessWidget {
  final String label;
  final String value;

  const _SummaryRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              value.isEmpty ? AppStrings.TABLE_VALUE_UNAVAILABLE : value,
              textAlign: TextAlign.right,
              style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
