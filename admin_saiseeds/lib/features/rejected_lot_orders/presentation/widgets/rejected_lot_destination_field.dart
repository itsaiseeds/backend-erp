import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../clients/data/models/client_address_model.dart';
import '../../../orders/presentation/widgets/delivery_to_field.dart';

/// The delivery destination for a rejected-lot order: always a place other
/// than the client's own address (the goods are coming off a farm, not out
/// of the client's own stock), so unlike [DeliveryToField] there is no
/// "same as client" toggle and no existing-child picker -- the admin fills
/// these fields in every time.
///
/// [partyName] is [DeliveryToValue.partyName] already computed by the parent
/// step from the Party + Farmer pickers that sit above this widget (not
/// re-picked here) -- this widget only owns the remaining destination
/// fields and folds that name into what it emits.
class RejectedLotDestinationField extends StatefulWidget {
  final String partyName;
  final DeliveryToValue initial;
  final ValueChanged<DeliveryToValue> onChanged;
  final bool enabled;

  const RejectedLotDestinationField({
    super.key,
    required this.partyName,
    required this.initial,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  State<RejectedLotDestinationField> createState() =>
      RejectedLotDestinationFieldState();
}

class RejectedLotDestinationFieldState
    extends State<RejectedLotDestinationField> {
  static const int _defaultCountryId = 1;

  late final TextEditingController _villageController = TextEditingController(
    text: widget.initial.villageName,
  );
  late final TextEditingController _transportController =
      TextEditingController(text: widget.initial.transportName);
  late final TextEditingController _contactController = TextEditingController(
    text: widget.initial.contactNumber,
  );
  late final TextEditingController _line1Controller = TextEditingController(
    text: widget.initial.newAddress?.line1 ?? '',
  );
  late final TextEditingController _line2Controller = TextEditingController(
    text: widget.initial.newAddress?.line2 ?? '',
  );
  late final TextEditingController _pincodeController = TextEditingController(
    text: widget.initial.newAddress?.pincode ?? '',
  );
  CityModel? _city;
  String? _cityError;
  String? _villageError;

  @override
  void initState() {
    super.initState();
    final ClientAddressModel? address = widget.initial.newAddress;
    if (address != null && address.cityId != 0) {
      _city = MetadataService.instance.cityById(address.cityId);
    }
  }

  @override
  void didUpdateWidget(covariant RejectedLotDestinationField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.partyName == oldWidget.partyName) return;
    // _emit() calls widget.onChanged, which setState()s the parent step --
    // doing that synchronously here would re-enter the parent's own build
    // (this runs while the parent is still rebuilding its child), corrupting
    // the element tree. Deferring to the next frame is the standard fix for
    // "notify an ancestor from didUpdateWidget".
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _emit();
    });
  }

  @override
  void dispose() {
    _villageController.dispose();
    _transportController.dispose();
    _contactController.dispose();
    _line1Controller.dispose();
    _line2Controller.dispose();
    _pincodeController.dispose();
    super.dispose();
  }

  void _emit() {
    final String line1 = _line1Controller.text.trim();
    final String pincode = _pincodeController.text.trim();
    if (widget.partyName.trim().isEmpty ||
        _villageController.text.trim().isEmpty ||
        _city == null ||
        line1.isEmpty ||
        pincode.isEmpty) {
      // Incomplete draft: nothing valid to send yet.
      widget.onChanged(const DeliveryToValue.none());
      return;
    }
    widget.onChanged(
      DeliveryToValue.newChild(
        partyName: widget.partyName,
        villageName: _villageController.text,
        transportName: _transportController.text,
        contactNumber: _contactController.text,
        address: ClientAddressModel(
          line1: line1,
          line2: _line2Controller.text.trim(),
          pincode: pincode,
          cityId: _city!.id,
          cityName: _city!.name,
          stateId: MetadataService.instance.stateOfCity(_city!.id)?.id ?? 0,
          stateName:
              MetadataService.instance.stateOfCity(_city!.id)?.name ?? '',
          countryId: _defaultCountryId,
        ),
      ),
    );
  }

  bool get _isValid {
    final bool villageValid = _villageController.text.trim().isNotEmpty;
    final bool cityValid = _city != null;

    setState(() {
      _villageError = villageValid
          ? null
          : AppStrings.VALIDATION_VILLAGE_NAME_REQUIRED;
      _cityError = cityValid ? null : AppStrings.VALIDATION_CITY_REQUIRED;
    });

    return villageValid && cityValid;
  }

  /// Exposed so the parent step can gate "Next" on a complete destination
  /// draft (the line-1/pincode validators run via the enclosing `Form`, and
  /// the party-name check lives on the Party/Farmer pickers above this
  /// widget, so only village / city need a manual check here).
  bool validate() => _isValid;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        AppTextField(
          controller: _villageController,
          label: AppStrings.DELIVERY_TO_VILLAGE_NAME,
          errorText: _villageError,
          enabled: widget.enabled,
          onChanged: (_) {
            if (_villageError != null) setState(() => _villageError = null);
            _emit();
          },
        ),
        const SizedBox(height: AppSpacing.smd),
        AppTextField(
          controller: _line1Controller,
          label: AppStrings.CLIENT_ADDRESS_LINE_1,
          enabled: widget.enabled,
          validator: FormValidators.requiredField,
          onChanged: (_) => _emit(),
        ),
        const SizedBox(height: AppSpacing.smd),
        AppTextField(
          controller: _line2Controller,
          label: AppStrings.CLIENT_ADDRESS_LINE_2,
          enabled: widget.enabled,
          onChanged: (_) => _emit(),
        ),
        const SizedBox(height: AppSpacing.smd),
        AppTextField(
          controller: _pincodeController,
          label: AppStrings.CLIENT_ADDRESS_PINCODE,
          enabled: widget.enabled,
          keyboardType: TextInputType.number,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          validator: FormValidators.requiredField,
          onChanged: (_) => _emit(),
        ),
        const SizedBox(height: AppSpacing.smd),
        CityPickerField(
          value: _city,
          enabled: widget.enabled,
          errorText: _cityError,
          onSelected: (selected) {
            setState(() {
              _city = selected;
              _cityError = null;
            });
            _emit();
          },
        ),
        const SizedBox(height: AppSpacing.smd),
        AppTextField(
          controller: _transportController,
          label: AppStrings.DELIVERY_TO_TRANSPORT_NAME,
          enabled: widget.enabled,
          onChanged: (_) => _emit(),
        ),
        const SizedBox(height: AppSpacing.smd),
        AppTextField(
          controller: _contactController,
          label: AppStrings.DELIVERY_TO_CONTACT_NUMBER,
          enabled: widget.enabled,
          keyboardType: TextInputType.phone,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(10),
          ],
          validator: FormValidators.optionalPhoneNumber,
          onChanged: (_) => _emit(),
        ),
      ],
    );
  }
}
