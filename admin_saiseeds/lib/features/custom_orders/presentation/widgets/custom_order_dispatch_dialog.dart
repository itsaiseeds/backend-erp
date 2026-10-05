import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/lot_number_picker_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../dispatch_challans/data/dispatch_lot_numbers_repository.dart';
import '../../../dispatch_challans/data/models/dispatch_lot_number_model.dart';
import '../../data/models/custom_order_model.dart';
import '../bloc/custom_orders_cubit.dart';

/// Dispatches a custom order over the same three steps as a regular one.
///
/// A custom order always goes on our own vehicle, so the driver and vehicle
/// are required here -- unlike a regular order, where an agency may fill them
/// in later.
class CustomOrderDispatchDialog extends StatefulWidget {
  final CustomOrderModel order;

  const CustomOrderDispatchDialog({super.key, required this.order});

  static Future<void> show(
    BuildContext context, {
    required CustomOrdersCubit cubit,
    required CustomOrderModel order,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<CustomOrdersCubit>.value(
        value: cubit,
        child: CustomOrderDispatchDialog(order: order),
      ),
    );
  }

  @override
  State<CustomOrderDispatchDialog> createState() =>
      _CustomOrderDispatchDialogState();
}

class _CustomOrderDispatchDialogState extends State<CustomOrderDispatchDialog> {
  static const List<String> _STEPS = [
    AppStrings.DISPATCH_STEP_TRANSPORT,
    AppStrings.DISPATCH_STEP_ITEMS,
    AppStrings.DISPATCH_STEP_SUMMARY,
  ];

  static const List<String> _CAPTIONS = [
    AppStrings.DISPATCH_STEP_TRANSPORT_CAPTION,
    AppStrings.DISPATCH_STEP_ITEMS_CAPTION,
    AppStrings.DISPATCH_STEP_SUMMARY_CAPTION,
  ];

  static const List<IconData> _ICONS = [
    Icons.local_shipping_outlined,
    Icons.numbers_outlined,
    Icons.fact_check_outlined,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _vehicleController = TextEditingController();
  final TextEditingController _driverNameController = TextEditingController();
  final TextEditingController _driverNumberController = TextEditingController();
  final Map<String, DispatchLotNumberModel?> _lotValues = {};
  List<DispatchLotNumberModel> _lotNumbers = const [];
  bool _isLoadingLots = true;
  bool _lotsUnavailable = false;

  int _stepIndex = 0;
  CityModel? _fromCity;
  String? _cityError;
  bool _isSubmitting = false;

  CustomOrderModel get _order => widget.order;

  List<CustomOrderItemModel> get _lines => _order.items;

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  @override
  void initState() {
    super.initState();
    for (final CustomOrderItemModel item in _lines) {
      _lotValues[_keyOf(item)] = null;
    }
    _loadLotNumbers();
  }

  Future<void> _loadLotNumbers() async {
    final List<DispatchLotNumberModel> lots =
        await DispatchLotNumbersRepository(
          apiClient: context.read<ApiClient>(),
        ).fetchLotNumbers();

    if (!mounted) return;
    setState(() {
      _lotNumbers = lots;
      _isLoadingLots = false;
      _lotsUnavailable = lots.isEmpty;
    });
  }

  void _setLot(String key, DispatchLotNumberModel lot) {
    setState(() => _lotValues[key] = lot);
  }

  String _lotFor(String key) => _lotValues[key]?.lotNumber.trim() ?? '';

  void _setFreeLot(String key, String typed) {
    setState(() => _lotValues[key] = DispatchLotNumberModel(lotNumber: typed));
  }

  @override
  void dispose() {
    _vehicleController.dispose();
    _driverNameController.dispose();
    _driverNumberController.dispose();
    super.dispose();
  }

  // A line is identified by product and weight together: the same product can
  // appear more than once at different packet weights.
  String _keyOf(CustomOrderItemModel item) =>
      '${item.productPublicId}|${item.packetWeight}';

  String _lineLabel(CustomOrderItemModel item) =>
      '${item.productName} - ${item.packetWeight} kg';

  bool _validateTransport() {
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
    if (index > _stepIndex && _stepIndex == 0 && !_validateTransport()) return;
    setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));
  }

  Future<void> _submit() async {
    if (!_validateTransport()) {
      setState(() => _stepIndex = 0);
      return;
    }

    setState(() => _isSubmitting = true);
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

    final bool succeeded = await cubit.dispatchCustomOrder(
      publicId: _order.publicId,
      body: {
        'from_city_id': _fromCity!.id,
        'driver_name': _driverNameController.text.trim(),
        'driver_number': _driverNumberController.text.trim(),
        'vehicle_number': _vehicleController.text.trim(),
        'items': [
          for (final CustomOrderItemModel item in _lines)
            {
              'product_public_id': item.productPublicId,
              'packet_weight': item.packetWeight,
              'lot_number': _lotFor(_keyOf(item)),
            },
        ],
      },
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.DISPATCHED_TITLE);
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
      icon: Icons.local_shipping_outlined,
      title: AppStrings.ORDER_DISPATCH_TITLE,
      subtitle: _CAPTIONS[_stepIndex],
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
      submitLabel: _isLastStep
          ? AppStrings.ORDER_DISPATCH
          : AppStrings.STEP_NEXT,
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
      case 0:
        return _buildTransportStep();
      case 1:
        return _buildItemsStep();
      default:
        return _buildSummaryStep();
    }
  }

  Widget _buildTransportStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: CityPickerField(
            value: _fromCity,
            fieldLabel: AppStrings.FIELD_FROM_CITY,
            enabled: !_isSubmitting,
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
            enabled: !_isSubmitting,
            validator: FormValidators.requiredField,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: AppTextField(
            controller: _driverNameController,
            label: AppStrings.FIELD_DRIVER_NAME,
            hint: AppStrings.FIELD_DRIVER_NAME_HINT,
            enabled: !_isSubmitting,
            validator: FormValidators.requiredField,
          ),
          right: AppTextField(
            controller: _driverNumberController,
            label: AppStrings.FIELD_DRIVER_NUMBER,
            hint: AppStrings.LOGIN_PHONE_HINT,
            keyboardType: TextInputType.phone,
            enabled: !_isSubmitting,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(
                FormValidators.PHONE_NUMBER_LENGTH,
              ),
            ],
            validator: FormValidators.phoneNumber,
          ),
        ),
      ],
    );
  }

  Widget _buildItemsStep() {
    if (_lines.isEmpty) {
      return Text(
        AppStrings.DISPATCH_ITEMS_EMPTY,
        style: AppTypography.bodyMedium.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    if (_isLoadingLots) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(AppSpacing.lg),
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final CustomOrderItemModel item in _lines) ...[
          LotNumberPickerField(
            value: _lotValues[_keyOf(item)],
            lotNumbers: _lotNumbers,
            enabled: !_isSubmitting,
            isUnavailable: _lotsUnavailable,
            onSelected: (lot) => _setLot(_keyOf(item), lot),
            onFreeEntry: (typed) => _setFreeLot(_keyOf(item), typed),
          ),
          const SizedBox(height: AppSpacing.md),
        ],
      ],
    );
  }

  Widget _buildSummaryStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _SummaryRow(
          label: AppStrings.FIELD_FROM_CITY,
          value: _fromCity?.name ?? '',
        ),
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
        const SizedBox(height: AppSpacing.md),
        SectionTitle(
          title: AppStrings.DISPATCH_SUMMARY_ITEMS,
          icon: Icons.inventory_2_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.sm),
        for (final CustomOrderItemModel item in _lines)
          _SummaryRow(label: _lineLabel(item), value: _lotFor(_keyOf(item))),
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
              style: AppTypography.bodySmall.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
