import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/layout/form_field_grid.dart';
import '../../data/models/godown_manager_model.dart';
import '../bloc/godown_managers_cubit.dart';

class GodownManagerFormDialog extends StatefulWidget {
  final GodownManagerModel? godownManager;

  const GodownManagerFormDialog({super.key, this.godownManager});

  static Future<void> show(
    BuildContext context, {
    required GodownManagersCubit cubit,
    GodownManagerModel? godownManager,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<GodownManagersCubit>.value(
        value: cubit,
        child: GodownManagerFormDialog(godownManager: godownManager),
      ),
    );
  }

  @override
  State<GodownManagerFormDialog> createState() =>
      _GodownManagerFormDialogState();
}

class _GodownManagerFormDialogState extends State<GodownManagerFormDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _emailController;
  late final TextEditingController _phoneController;

  bool _isSubmitting = false;

  bool get _isEditing => widget.godownManager != null;

  @override
  void initState() {
    super.initState();
    final GodownManagerModel? manager = widget.godownManager;
    _nameController = TextEditingController(text: manager?.name ?? '');
    _emailController = TextEditingController(text: manager?.email ?? '');
    _phoneController = TextEditingController(text: manager?.phoneNumber ?? '');
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

    final GodownManagersCubit cubit = context.read<GodownManagersCubit>();
    final String email = _emailController.text.trim();

    final bool succeeded = _isEditing
        ? await cubit.updateGodownManager(
            id: widget.godownManager!.id,
            name: _nameController.text.trim(),
            phoneNumber: _phoneController.text.trim(),
            email: email.isEmpty ? null : email,
          )
        : await cubit.createGodownManager(
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
            ? AppStrings.GODOWN_MANAGER_UPDATED_TITLE
            : AppStrings.GODOWN_MANAGER_CREATED_TITLE,
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
      icon: Icons.warehouse_outlined,
      title: _isEditing
          ? AppStrings.EDIT_GODOWN_MANAGER
          : AppStrings.ADD_GODOWN_MANAGER,
      subtitle: _isEditing
          ? AppStrings.EDIT_GODOWN_MANAGER_SUBTITLE
          : AppStrings.ADD_GODOWN_MANAGER_SUBTITLE,
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
