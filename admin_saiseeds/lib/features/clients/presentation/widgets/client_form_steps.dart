import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/models/state_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../data/models/client_address_model.dart';
import '../../data/models/client_contact_model.dart';
import '../../data/models/transport_agency_model.dart';

enum ClientFormStep { details, addresses, contacts, transport }

extension ClientFormStepX on ClientFormStep {
  String get label {
    switch (this) {
      case ClientFormStep.details:
        return AppStrings.CLIENT_STEP_DETAILS;
      case ClientFormStep.addresses:
        return AppStrings.CLIENT_STEP_ADDRESSES;
      case ClientFormStep.contacts:
        return AppStrings.CLIENT_STEP_CONTACTS;
      case ClientFormStep.transport:
        return AppStrings.CLIENT_STEP_TRANSPORT;
    }
  }
}

class ClientStepIndicator extends StatelessWidget {
  final ClientFormStep current;
  final ValueChanged<ClientFormStep>? onStepTapped;

  const ClientStepIndicator({
    super.key,
    required this.current,
    this.onStepTapped,
  });

  @override
  Widget build(BuildContext context) {
    final int currentIndex = ClientFormStep.values.indexOf(current);

    return Row(
      children: [
        for (final step in ClientFormStep.values) ...[
          if (step.index > 0)
            Expanded(
              child: Container(
                height: AppSizes.borderThin,
                margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                color: step.index <= currentIndex
                    ? AppColors.PRIMARY
                    : AppColors.BORDER,
              ),
            ),
          _StepDot(
            index: step.index,
            label: step.label,
            isActive: step.index == currentIndex,
            isComplete: step.index < currentIndex,
            onTap: onStepTapped == null ? null : () => onStepTapped!(step),
          ),
        ],
      ],
    );
  }
}

class _StepDot extends StatelessWidget {
  final int index;
  final String label;
  final bool isActive;
  final bool isComplete;
  final VoidCallback? onTap;

  const _StepDot({
    required this.index,
    required this.label,
    required this.isActive,
    required this.isComplete,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isHighlighted = isActive || isComplete;

    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            curve: Curves.easeOutCubic,
            width: AppSizes.stepDotSize,
            height: AppSizes.stepDotSize,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isHighlighted ? AppColors.PRIMARY : AppColors.SURFACE,
              border: Border.all(
                color: isHighlighted ? AppColors.PRIMARY : AppColors.BORDER,
              ),
            ),
            child: isComplete
                ? const Icon(
                    Icons.check_rounded,
                    size: AppSizes.iconSm,
                    color: AppColors.TEXT_ON_PRIMARY,
                  )
                : Text(
                    '${index + 1}',
                    style: AppTypography.labelMedium.copyWith(
                      color: isHighlighted
                          ? AppColors.TEXT_ON_PRIMARY
                          : AppColors.TEXT_SECONDARY,
                    ),
                  ),
          ),
          const SizedBox(height: AppSpacing.xxs),
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: isHighlighted
                  ? AppColors.TEXT_PRIMARY
                  : AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ),
    );
  }
}

class EntryCard extends StatefulWidget {
  final String title;
  final String summary;
  final Widget child;
  final VoidCallback? onRemove;
  final bool initiallyExpanded;
  final bool isPrimary;

  const EntryCard({
    super.key,
    required this.title,
    required this.child,
    this.summary = '',
    this.onRemove,
    this.initiallyExpanded = true,
    this.isPrimary = false,
  });

  @override
  State<EntryCard> createState() => _EntryCardState();
}

class _EntryCardState extends State<EntryCard> {
  static const Duration _duration = Duration(milliseconds: 200);

  late bool _isExpanded = widget.initiallyExpanded;

  void _toggle() => setState(() => _isExpanded = !_isExpanded);

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(
          color: _isExpanded ? AppColors.PRIMARY : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: _toggle,
            borderRadius: BorderRadius.circular(AppRadius.md),
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.md),
              child: Row(
                children: [
                  AnimatedRotation(
                    duration: _duration,
                    curve: Curves.easeOutCubic,
                    turns: _isExpanded ? 0.25 : 0,
                    child: const Icon(
                      Icons.chevron_right_rounded,
                      size: AppSizes.iconMd,
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(widget.title, style: AppTypography.labelStrong),
                        if (!_isExpanded && widget.summary.trim().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: AppSpacing.xxs),
                            child: Text(
                              widget.summary,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: AppTypography.bodySmall.copyWith(
                                color: AppColors.TEXT_SECONDARY,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  if (widget.isPrimary) ...[
                    const SizedBox(width: AppSpacing.sm),
                    const AppBadge(
                      label: AppStrings.CLIENT_PRIMARY_BADGE,
                      variant: AppBadgeVariant.info,
                    ),
                  ],
                  if (widget.onRemove != null) ...[
                    const SizedBox(width: AppSpacing.sm),
                    IconActionButton(
                      icon: Icons.delete_outline_rounded,
                      tooltip: AppStrings.CLIENT_REMOVE_ENTRY,
                      type: IconActionType.error,
                      onPressed: widget.onRemove,
                    ),
                  ],
                ],
              ),
            ),
          ),
          AnimatedCrossFade(
            duration: _duration,
            sizeCurve: Curves.easeOutCubic,
            crossFadeState: _isExpanded
                ? CrossFadeState.showFirst
                : CrossFadeState.showSecond,
            firstChild: Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.md,
                0,
                AppSpacing.md,
                AppSpacing.md,
              ),
              child: widget.child,
            ),
            secondChild: const SizedBox(width: double.infinity),
          ),
        ],
      ),
    );
  }
}

class AddressStepCard extends StatefulWidget {
  final ClientAddressModel address;
  final int index;
  final bool canRemove;
  final ValueChanged<ClientAddressModel> onChanged;
  final VoidCallback onRemove;
  final VoidCallback onMakePrimary;
  final bool enabled;
  final bool initiallyExpanded;

  const AddressStepCard({
    super.key,
    required this.address,
    required this.index,
    required this.canRemove,
    required this.onChanged,
    required this.onRemove,
    required this.onMakePrimary,
    this.enabled = true,
    this.initiallyExpanded = true,
  });

  @override
  State<AddressStepCard> createState() => _AddressStepCardState();
}

class _AddressStepCardState extends State<AddressStepCard> {
  static String _summary(ClientAddressModel address) {
    final List<String> parts = [
      if (address.label.trim().isNotEmpty) address.label.trim(),
      if (address.line1.trim().isNotEmpty) address.line1.trim(),
      if (address.cityName.trim().isNotEmpty) address.cityName.trim(),
      if (address.pincode.trim().isNotEmpty) address.pincode.trim(),
    ];
    return parts.join(', ');
  }

  late final TextEditingController _label;
  late final TextEditingController _line1;
  late final TextEditingController _line2;
  late final TextEditingController _pincode;

  @override
  void initState() {
    super.initState();
    _label = TextEditingController(text: widget.address.label);
    _line1 = TextEditingController(text: widget.address.line1);
    _line2 = TextEditingController(text: widget.address.line2);
    _pincode = TextEditingController(text: widget.address.pincode);
  }

  @override
  void dispose() {
    _label.dispose();
    _line1.dispose();
    _line2.dispose();
    _pincode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ClientAddressModel address = widget.address;
    final CityModel? city = address.cityId == 0
        ? null
        : MetadataService.instance.cityById(address.cityId);

    return EntryCard(
      title: '${AppStrings.CLIENT_STEP_ADDRESSES} ${widget.index + 1}',
      summary: _summary(address),
      isPrimary: address.isPrimary,
      initiallyExpanded: widget.initiallyExpanded,
      onRemove: widget.canRemove && widget.enabled ? widget.onRemove : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppTextField(
            controller: _label,
            label: AppStrings.CLIENT_ADDRESS_LABEL,
            enabled: widget.enabled,
            onChanged: (value) =>
                widget.onChanged(address.copyWith(label: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          AppTextField(
            controller: _line1,
            label: AppStrings.CLIENT_ADDRESS_LINE_1,
            enabled: widget.enabled,
            validator: FormValidators.requiredField,
            onChanged: (value) =>
                widget.onChanged(address.copyWith(line1: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          AppTextField(
            controller: _line2,
            label: AppStrings.CLIENT_ADDRESS_LINE_2,
            enabled: widget.enabled,
            onChanged: (value) =>
                widget.onChanged(address.copyWith(line2: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          AppTextField(
            controller: _pincode,
            label: AppStrings.CLIENT_ADDRESS_PINCODE,
            enabled: widget.enabled,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(_pincodeLength),
            ],
            validator: FormValidators.requiredField,
            onChanged: (value) =>
                widget.onChanged(address.copyWith(pincode: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          CityPickerField(
            value: city,
            enabled: widget.enabled,
            errorText: address.cityId == 0
                ? AppStrings.VALIDATION_CITY_REQUIRED
                : null,
            onSelected: (selected) {
              final StateModel? state = MetadataService.instance.stateOfCity(
                selected.id,
              );
              widget.onChanged(
                address.copyWith(
                  cityId: selected.id,
                  cityName: selected.name,
                  stateId: state?.id ?? address.stateId,
                  stateName: state?.name ?? address.stateName,
                  countryId: address.countryId == 0
                      ? _defaultCountryId
                      : address.countryId,
                ),
              );
            },
          ),
          const SizedBox(height: AppSpacing.smd),
          _PrimaryToggle(
            isPrimary: address.isPrimary,
            enabled: widget.enabled,
            onSelected: widget.onMakePrimary,
          ),
        ],
      ),
    );
  }

  static const int _pincodeLength = 6;
  static const int _defaultCountryId = 1;
}

class ContactStepCard extends StatefulWidget {
  final ClientContactModel contact;
  final int index;
  final bool canRemove;
  final ValueChanged<ClientContactModel> onChanged;
  final VoidCallback onRemove;
  final VoidCallback onMakePrimary;
  final bool enabled;
  final bool initiallyExpanded;

  const ContactStepCard({
    super.key,
    required this.contact,
    required this.index,
    required this.canRemove,
    required this.onChanged,
    required this.onRemove,
    required this.onMakePrimary,
    this.enabled = true,
    this.initiallyExpanded = true,
  });

  @override
  State<ContactStepCard> createState() => _ContactStepCardState();
}

class _ContactStepCardState extends State<ContactStepCard> {
  static const int _phoneLength = 10;

  late final TextEditingController _name;
  late final TextEditingController _phone;
  late final TextEditingController _role;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.contact.name);
    _phone = TextEditingController(text: widget.contact.phoneNumber);
    _role = TextEditingController(text: widget.contact.role);
  }

  @override
  void dispose() {
    _name.dispose();
    _phone.dispose();
    _role.dispose();
    super.dispose();
  }

  ClientContactModel _copy({String? name, String? phoneNumber, String? role}) {
    return ClientContactModel(
      name: name ?? widget.contact.name,
      phoneNumber: phoneNumber ?? widget.contact.phoneNumber,
      role: role ?? widget.contact.role,
      isPrimary: widget.contact.isPrimary,
    );
  }

  @override
  Widget build(BuildContext context) {
    return EntryCard(
      title: '${AppStrings.CLIENT_STEP_CONTACTS} ${widget.index + 1}',
      summary: [
        widget.contact.name,
        widget.contact.phoneNumber,
      ].where((part) => part.trim().isNotEmpty).join(' · '),
      isPrimary: widget.contact.isPrimary,
      initiallyExpanded: widget.initiallyExpanded,
      onRemove: widget.canRemove && widget.enabled ? widget.onRemove : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppTextField(
            controller: _name,
            label: AppStrings.CLIENT_CONTACT_NAME,
            enabled: widget.enabled,
            validator: FormValidators.requiredField,
            onChanged: (value) => widget.onChanged(_copy(name: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          AppTextField(
            controller: _phone,
            label: AppStrings.CLIENT_CONTACT_PHONE,
            enabled: widget.enabled,
            prefixText: AppStrings.PHONE_COUNTRY_CODE_IN,
            keyboardType: TextInputType.phone,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(_phoneLength),
            ],
            validator: FormValidators.phoneNumber,
            onChanged: (value) => widget.onChanged(_copy(phoneNumber: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          AppTextField(
            controller: _role,
            label: AppStrings.CLIENT_CONTACT_ROLE,
            enabled: widget.enabled,
            onChanged: (value) => widget.onChanged(_copy(role: value)),
          ),
          const SizedBox(height: AppSpacing.smd),
          _PrimaryToggle(
            isPrimary: widget.contact.isPrimary,
            enabled: widget.enabled,
            onSelected: widget.onMakePrimary,
          ),
        ],
      ),
    );
  }
}

class TransportStepCard extends StatefulWidget {
  final TransportAgencyModel agency;
  final int index;
  final bool canRemove;
  final ValueChanged<TransportAgencyModel> onChanged;
  final VoidCallback onRemove;
  final VoidCallback onMakePrimary;
  final bool enabled;
  final bool initiallyExpanded;

  const TransportStepCard({
    super.key,
    required this.agency,
    required this.index,
    required this.canRemove,
    required this.onChanged,
    required this.onRemove,
    required this.onMakePrimary,
    this.enabled = true,
    this.initiallyExpanded = true,
  });

  @override
  State<TransportStepCard> createState() => _TransportStepCardState();
}

class _TransportStepCardState extends State<TransportStepCard> {
  late final TextEditingController _name;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.agency.name);
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return EntryCard(
      title: '${AppStrings.CLIENT_STEP_TRANSPORT} ${widget.index + 1}',
      summary: widget.agency.name,
      isPrimary: widget.agency.isPrimary,
      initiallyExpanded: widget.initiallyExpanded,
      onRemove: widget.canRemove && widget.enabled ? widget.onRemove : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          AppTextField(
            controller: _name,
            label: AppStrings.CLIENT_TRANSPORT_NAME,
            enabled: widget.enabled,
            validator: FormValidators.requiredField,
            onChanged: (value) => widget.onChanged(
              TransportAgencyModel(
                name: value,
                isPrimary: widget.agency.isPrimary,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.smd),
          _PrimaryToggle(
            isPrimary: widget.agency.isPrimary,
            enabled: widget.enabled,
            onSelected: widget.onMakePrimary,
          ),
        ],
      ),
    );
  }
}

class _PrimaryToggle extends StatelessWidget {
  final bool isPrimary;
  final bool enabled;
  final VoidCallback onSelected;

  const _PrimaryToggle({
    required this.isPrimary,
    required this.enabled,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled && !isPrimary ? onSelected : null,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isPrimary
                ? Icons.radio_button_checked_rounded
                : Icons.radio_button_unchecked_rounded,
            size: AppSizes.iconMd,
            color: isPrimary ? AppColors.PRIMARY : AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            AppStrings.CLIENT_MARK_PRIMARY,
            style: AppTypography.bodyMedium.copyWith(
              color: isPrimary
                  ? AppColors.TEXT_PRIMARY
                  : AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ),
    );
  }
}
