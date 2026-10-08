import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/app_toggle_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/client_address_model.dart';
import '../../data/models/child_org_model.dart';

/// The ``booked_for.address`` sub-object -- just the write fields
/// ``ChildOrgAddressSerializer`` accepts, deliberately narrower than
/// [ClientAddressModel.toWriteJson] which also carries ``label``/``is_primary``.
Map<String, dynamic> _childAddressJson(ClientAddressModel address) => {
  'line_1': address.line1,
  'line_2': address.line2,
  'pincode': address.pincode,
  'city': address.cityId,
  'state': address.stateId,
  'country': address.countryId,
};

/// What the "Delivery To" section currently describes, as something a caller
/// can turn straight into a `booked_for` PATCH/POST value.
///
/// [untouched] exists only for an edit form: the user never opened this
/// section, so the key must be left out of the request entirely rather than
/// sent as `null` (which would explicitly clear an existing value).
class DeliveryToValue {
  final bool untouched;
  final ChildOrgModel? existing;
  final String partyName;
  final String villageName;
  final String transportName;
  final String contactNumber;
  final ClientAddressModel? newAddress;

  const DeliveryToValue._({
    this.untouched = false,
    this.existing,
    this.partyName = '',
    this.villageName = '',
    this.transportName = '',
    this.contactNumber = '',
    this.newAddress,
  });

  const DeliveryToValue.untouchedValue() : this._(untouched: true);

  const DeliveryToValue.none() : this._();

  const DeliveryToValue.existingChild(ChildOrgModel child)
    : this._(existing: child);

  const DeliveryToValue.newChild({
    required String partyName,
    required String villageName,
    required ClientAddressModel address,
    String transportName = '',
    String contactNumber = '',
  }) : this._(
         partyName: partyName,
         villageName: villageName,
         transportName: transportName,
         contactNumber: contactNumber,
         newAddress: address,
       );

  bool get isSet => existing != null || newAddress != null;

  /// `true` when the section describes "same as client" -- send a literal
  /// `null`. Only meaningful when [untouched] is false.
  bool get isCleared => !untouched && !isSet;

  /// The `booked_for` request value: omit the key for [untouched], `null`
  /// for "same as client", `{id: ...}` for an existing child, or the full
  /// creation object for a new one.
  Object? toRequestValue() {
    if (existing != null) return {'id': existing!.id};
    if (newAddress != null) {
      return {
        'party_name': partyName.trim(),
        'village_name': villageName.trim(),
        'address': _childAddressJson(newAddress!),
        if (transportName.trim().isNotEmpty)
          'transport_name': transportName.trim(),
        if (contactNumber.trim().isNotEmpty)
          'contact_number': contactNumber.trim(),
      };
    }
    return null;
  }
}

/// The "Delivery To" section on an order / custom order form: a toggle that
/// reveals a picker for the client's existing delivery places, or a small
/// form to add a new one. Mirrors the mobile app's equivalent step.
class DeliveryToField extends StatefulWidget {
  final ApiClient apiClient;
  final String clientPublicId;
  final DeliveryToValue initial;
  final ValueChanged<DeliveryToValue> onChanged;
  final bool enabled;

  const DeliveryToField({
    super.key,
    required this.apiClient,
    required this.clientPublicId,
    required this.initial,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  State<DeliveryToField> createState() => _DeliveryToFieldState();
}

class _DeliveryToFieldState extends State<DeliveryToField> {
  static const int _defaultCountryId = 1;

  late bool _isOn = widget.initial.isSet;
  late ChildOrgModel? _selected = widget.initial.existing;
  bool _isAddingNew = false;

  late final TextEditingController _partyController = TextEditingController(
    text: widget.initial.partyName,
  );
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
  String? _partyError;
  String? _villageError;

  List<ChildOrgModel> _children = const [];
  bool _isLoadingChildren = false;
  String? _loadedForClient;

  @override
  void initState() {
    super.initState();
    final ClientAddressModel? address = widget.initial.newAddress;
    if (address != null && address.cityId != 0) {
      _city = MetadataService.instance.cityById(address.cityId);
    }
    _isAddingNew = widget.initial.newAddress != null;
    if (_isOn) _loadChildren();
  }

  @override
  void didUpdateWidget(covariant DeliveryToField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clientPublicId != widget.clientPublicId) {
      _children = const [];
      _loadedForClient = null;
      if (_isOn) _loadChildren();
    }
  }

  @override
  void dispose() {
    _partyController.dispose();
    _villageController.dispose();
    _transportController.dispose();
    _contactController.dispose();
    _line1Controller.dispose();
    _line2Controller.dispose();
    _pincodeController.dispose();
    super.dispose();
  }

  Future<void> _loadChildren() async {
    if (widget.clientPublicId.isEmpty || _loadedForClient == widget.clientPublicId) {
      return;
    }

    setState(() => _isLoadingChildren = true);
    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: widget.apiClient,
      );
      final List<ChildOrgModel> children = await repository.fetchClientChildren(
        widget.clientPublicId,
      );
      if (!mounted || widget.clientPublicId != _pendingClientId) return;
      setState(() {
        _children = children;
        _isLoadingChildren = false;
        _loadedForClient = widget.clientPublicId;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingChildren = false);
    }
  }

  String get _pendingClientId => widget.clientPublicId;

  void _emit() {
    if (!_isOn) {
      widget.onChanged(const DeliveryToValue.none());
      return;
    }
    if (!_isAddingNew && _selected != null) {
      widget.onChanged(DeliveryToValue.existingChild(_selected!));
      return;
    }
    if (_isAddingNew) {
      final String line1 = _line1Controller.text.trim();
      final String pincode = _pincodeController.text.trim();
      if (_partyController.text.trim().isEmpty ||
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
          partyName: _partyController.text,
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
            // Admin's metadata catalogue tracks city -> state only (one
            // country in this deployment), matching AddressStepCard's
            // identical hardcode for a client's own address.
            countryId: _defaultCountryId,
          ),
        ),
      );
      return;
    }
    widget.onChanged(const DeliveryToValue.none());
  }

  void _toggle(bool value) {
    setState(() {
      _isOn = value;
      if (value) {
        _loadChildren();
      } else {
        _selected = null;
        _isAddingNew = false;
      }
    });
    _emit();
  }

  void _selectExisting(ChildOrgModel child) {
    setState(() {
      _selected = child;
      _isAddingNew = false;
    });
    _emit();
  }

  void _startNew() {
    setState(() {
      _isAddingNew = true;
      _selected = null;
    });
    _emit();
  }

  void _useExisting() {
    setState(() => _isAddingNew = false);
    _emit();
  }

  bool get _validateNewForm {
    final bool partyValid = _partyController.text.trim().isNotEmpty;
    final bool villageValid = _villageController.text.trim().isNotEmpty;
    final bool cityValid = _city != null;

    setState(() {
      _partyError = partyValid ? null : AppStrings.VALIDATION_PARTY_NAME_REQUIRED;
      _villageError = villageValid
          ? null
          : AppStrings.VALIDATION_VILLAGE_NAME_REQUIRED;
      _cityError = cityValid ? null : AppStrings.VALIDATION_CITY_REQUIRED;
    });

    return partyValid && villageValid && cityValid;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        AppToggleField(
          label: AppStrings.DELIVERY_TO_TOGGLE,
          description: AppStrings.DELIVERY_TO_TOGGLE_HINT,
          value: _isOn,
          onChanged: widget.enabled ? _toggle : null,
        ),
        if (_isOn) ...[
          const SizedBox(height: AppSpacing.md),
          SectionTitle(
            title: AppStrings.DELIVERY_TO_SECTION,
            icon: Icons.alt_route_outlined,
          ),
          const SizedBox(height: AppSpacing.smd),
          if (!_isAddingNew) ...[
            SearchableField<ChildOrgModel>(
              label: AppStrings.DELIVERY_TO_PICK,
              hintText: _isLoadingChildren
                  ? AppStrings.LOADING
                  : AppStrings.DELIVERY_TO_PICK_HINT,
              value: _selected,
              items: _children,
              itemToString: (child) => child.displayLabel,
              isSame: (a, b) => a.id == b.id,
              enabled: widget.enabled && !_isLoadingChildren,
              onSelected: _selectExisting,
            ),
            const SizedBox(height: AppSpacing.sm),
            _AddNewLink(
              label: AppStrings.DELIVERY_TO_ADD_NEW,
              enabled: widget.enabled,
              onTap: _startNew,
            ),
          ] else ...[
            if (_children.isNotEmpty)
              _AddNewLink(
                label: AppStrings.DELIVERY_TO_USE_EXISTING,
                enabled: widget.enabled,
                onTap: _useExisting,
              ),
            if (_children.isNotEmpty) const SizedBox(height: AppSpacing.smd),
            AppTextField(
              controller: _partyController,
              label: AppStrings.DELIVERY_TO_PARTY_NAME,
              errorText: _partyError,
              enabled: widget.enabled,
              onChanged: (_) {
                if (_partyError != null) setState(() => _partyError = null);
                _emit();
              },
            ),
            const SizedBox(height: AppSpacing.smd),
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
        ],
      ],
    );
  }

  /// Exposed so a parent step can gate "Next"/"Save" on a complete new-child
  /// draft instead of silently dropping it (see [_emit]'s incomplete-draft
  /// fallback).
  bool validateIfAddingNew() => !_isOn || !_isAddingNew || _validateNewForm;
}

class _AddNewLink extends StatelessWidget {
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  const _AddNewLink({
    required this.label,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onTap : null,
      behavior: HitTestBehavior.opaque,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.add_circle_outline_rounded,
            size: AppSizes.iconSm,
            color: enabled ? AppColors.PRIMARY : AppColors.TEXT_DISABLED,
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: enabled ? AppColors.PRIMARY : AppColors.TEXT_DISABLED,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
