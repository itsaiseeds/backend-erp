import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../bloc/parties_cubit.dart';

class PartyFormDialog extends StatefulWidget {
  const PartyFormDialog({super.key});

  static Future<void> show(
    BuildContext context, {
    required PartiesCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<PartiesCubit>.value(
        value: cubit,
        child: const PartyFormDialog(),
      ),
    );
  }

  @override
  State<PartyFormDialog> createState() => _PartyFormDialogState();
}

class _PartyFormDialogState extends State<PartyFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _contactController = TextEditingController();

  CityModel? _selectedCity;
  bool _isSubmitting = false;
  String? _cityError;

  @override
  void dispose() {
    _nameController.dispose();
    _contactController.dispose();
    super.dispose();
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

    final bool succeeded = await cubit.createParty(
      name: _nameController.text.trim(),
      cityId: _selectedCity!.id,
      contactNumber: contact.isEmpty ? null : contact,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.PARTY_CREATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.handshake_outlined,
      title: AppStrings.ADD_PARTY,
      subtitle: AppStrings.ADD_PARTY_SUBTITLE,
      submitLabel: AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            AppTextField(
              controller: _nameController,
              label: AppStrings.COLUMN_PARTY_NAME,
              hint: AppStrings.FIELD_PARTY_NAME_HINT,
              enabled: !_isSubmitting,
              validator: FormValidators.requiredField,
            ),
            const SizedBox(height: AppSpacing.md),
            CityPickerField(
              value: _selectedCity,
              enabled: !_isSubmitting,
              errorText: _cityError,
              onSelected: (city) => setState(() {
                _selectedCity = city;
                _cityError = null;
              }),
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _contactController,
              label: AppStrings.COLUMN_PARTY_CONTACT,
              hint: AppStrings.FIELD_PARTY_CONTACT_HINT,
              keyboardType: TextInputType.phone,
              enabled: !_isSubmitting,
              inputFormatters: [
                FilteringTextInputFormatter.digitsOnly,
                LengthLimitingTextInputFormatter(
                  FormValidators.PHONE_NUMBER_LENGTH,
                ),
              ],
              validator: FormValidators.optionalPhoneNumber,
            ),
          ],
        ),
      ),
    );
  }
}
