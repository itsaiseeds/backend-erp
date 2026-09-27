import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../data/models/order_model.dart';
import '../bloc/orders_cubit.dart';

class OrderLrDialog extends StatefulWidget {
  final OrderModel order;

  const OrderLrDialog({super.key, required this.order});

  static Future<void> show(
    BuildContext context,
    OrderModel order, {
    required OrdersCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OrdersCubit>.value(
        value: cubit,
        child: OrderLrDialog(order: order),
      ),
    );
  }

  @override
  State<OrderLrDialog> createState() => _OrderLrDialogState();
}

class _OrderLrDialogState extends State<OrderLrDialog> {
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _lrController = TextEditingController();

  bool _isSubmitting = false;

  @override
  void dispose() {
    _lrController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isSubmitting = true);

    final OrdersCubit cubit = context.read<OrdersCubit>();

    final bool succeeded = await cubit.uploadLrNumber(
      publicId: widget.order.publicId,
      lrNumber: _lrController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.CHALLAN_LR_SAVED);
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
      icon: Icons.receipt_long_outlined,
      title: AppStrings.CHALLAN_LR_TITLE,
      subtitle: AppStrings.ORDER_LR_SUBTITLE,
      width: AppSizes.formDialogCompactWidth,
      submitLabel: AppStrings.SAVE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: AppTextField(
          controller: _lrController,
          label: AppStrings.COLUMN_LR_NUMBER,
          hint: AppStrings.FIELD_LR_NUMBER_HINT,
          enabled: !_isSubmitting,
          validator: FormValidators.requiredField,
        ),
      ),
    );
  }
}
