import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/layout/form_field_grid.dart';
import '../../data/models/lab_tester_model.dart';
import '../bloc/lab_testers_cubit.dart';

class LabTesterFormDialog extends StatefulWidget {
  final LabTesterModel? labTester;

  const LabTesterFormDialog({super.key, this.labTester});

  static Future<void> show(
    BuildContext context, {
    required LabTestersCubit cubit,
    LabTesterModel? labTester,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<LabTestersCubit>.value(
        value: cubit,
        child: LabTesterFormDialog(labTester: labTester),
      ),
    );
  }

  @override
  State<LabTesterFormDialog> createState() => _LabTesterFormDialogState();
}

class _LabTesterFormDialogState extends State<LabTesterFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;

  bool _isSubmitting = false;

  bool get _isEditing => widget.labTester != null;

  @override
  void initState() {
    super.initState();
    final LabTesterModel? tester = widget.labTester;
    _nameController = TextEditingController(text: tester?.name ?? '');
    _emailController = TextEditingController(text: tester?.email ?? '');
    _phoneController = TextEditingController(text: tester?.phoneNumber ?? '');
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
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final LabTestersCubit cubit = context.read<LabTestersCubit>();
    final String email = _emailController.text.trim();

    final bool succeeded = _isEditing
        ? await cubit.updateLabTester(
            id: widget.labTester!.id,
            name: _nameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            email: email.isEmpty ? null : email,
          )
        : await cubit.createLabTester(
            name: _nameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            email: email.isEmpty ? null : email,
          );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        _isEditing
            ? AppStrings.LAB_TESTER_UPDATED_TITLE
            : AppStrings.LAB_TESTER_CREATED_TITLE,
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
      icon: Icons.biotech_outlined,
      title: _isEditing ? AppStrings.EDIT_LAB_TESTER : AppStrings.ADD_LAB_TESTER,
      subtitle: _isEditing
          ? AppStrings.EDIT_LAB_TESTER_SUBTITLE
          : AppStrings.ADD_LAB_TESTER_SUBTITLE,
      submitLabel: _isEditing ? AppStrings.UPDATE : AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: FormFieldGrid(
          fields: [
            AppTextField(
              controller: _nameController,
              label: AppStrings.FIELD_NAME,
              hint: AppStrings.FIELD_NAME_HINT,
              enabled: !_isSubmitting,
              validator: FormValidators.requiredField,
            ),
            AppTextField(
              controller: _emailController,
              label: AppStrings.FIELD_EMAIL_OPTIONAL,
              hint: AppStrings.FIELD_EMAIL_HINT,
              keyboardType: TextInputType.emailAddress,
              enabled: !_isSubmitting,
              validator: FormValidators.optionalEmail,
            ),
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
          ],
        ),
      ),
    );
  }
}
