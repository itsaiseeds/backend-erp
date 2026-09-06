import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/city_model.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/city_picker_field.dart';
import '../../data/models/sales_person_model.dart';
import '../bloc/sales_people_cubit.dart';

class SalesPersonFormDialog extends StatefulWidget {
  final SalesPersonModel? salesPerson;

  const SalesPersonFormDialog({super.key, this.salesPerson});

  static Future<void> show(
    BuildContext context, {
    required SalesPeopleCubit cubit,
    SalesPersonModel? salesPerson,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<SalesPeopleCubit>.value(
        value: cubit,
        child: SalesPersonFormDialog(salesPerson: salesPerson),
      ),
    );
  }

  @override
  State<SalesPersonFormDialog> createState() => _SalesPersonFormDialogState();
}

class _SalesPersonFormDialogState extends State<SalesPersonFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;

  CityModel? _selectedCity;
  bool _isSubmitting = false;
  String? _cityError;

  bool get _isEditing => widget.salesPerson != null;

  @override
  void initState() {
    super.initState();
    final SalesPersonModel? person = widget.salesPerson;
    _nameController = TextEditingController(text: person?.name ?? '');
    _emailController = TextEditingController(text: person?.email ?? '');
    _phoneController = TextEditingController(text: person?.phoneNumber ?? '');
    _selectedCity =
        MetadataService.instance.cityById(person?.cityId) ?? person?.city;
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCityValid = _selectedCity != null;

    setState(
      () => _cityError = isCityValid
          ? null
          : AppStrings.VALIDATION_CITY_REQUIRED,
    );

    if (!isFormValid || !isCityValid) return;

    setState(() => _isSubmitting = true);

    final SalesPeopleCubit cubit = context.read<SalesPeopleCubit>();
    final String email = _emailController.text.trim();

    final bool succeeded = _isEditing
        ? await cubit.updateSalesPerson(
            id: widget.salesPerson!.id,
            name: _nameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            cityId: _selectedCity!.id,
            email: email.isEmpty ? null : email,
          )
        : await cubit.createSalesPerson(
            name: _nameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            cityId: _selectedCity!.id,
            email: email.isEmpty ? null : email,
          );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        _isEditing
            ? AppStrings.SALES_PERSON_UPDATED_TITLE
            : AppStrings.SALES_PERSON_CREATED_TITLE,
      );
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
      icon: Icons.groups_outlined,
      title: _isEditing
          ? AppStrings.EDIT_SALES_PERSON
          : AppStrings.ADD_SALES_PERSON,
      subtitle: _isEditing
          ? AppStrings.EDIT_SALES_PERSON_SUBTITLE
          : AppStrings.ADD_SALES_PERSON_SUBTITLE,
      submitLabel: _isEditing ? AppStrings.UPDATE : AppStrings.CREATE,
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
              label: AppStrings.FIELD_NAME,
              hint: AppStrings.FIELD_NAME_HINT,
              enabled: !_isSubmitting,
              validator: FormValidators.requiredField,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _emailController,
              label: AppStrings.FIELD_EMAIL_OPTIONAL,
              hint: AppStrings.FIELD_EMAIL_HINT,
              keyboardType: TextInputType.emailAddress,
              enabled: !_isSubmitting,
              validator: FormValidators.optionalEmail,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _phoneController,
              label: AppStrings.PHONE_NUMBER,
              hint: AppStrings.FIELD_PHONE_HINT,
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
          ],
        ),
      ),
    );
  }
}
