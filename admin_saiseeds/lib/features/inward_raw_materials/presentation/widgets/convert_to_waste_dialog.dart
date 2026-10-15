import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../data/models/inward_raw_material_model.dart';
import '../bloc/inward_raw_materials_cubit.dart';

const int _REASON_MAX_LENGTH = 255;

/// Writes a rejected lot off as waste. `reason` is optional -- left blank,
/// the server fills in its own default naming the lot and farmer.
class ConvertToWasteDialog extends StatefulWidget {
  final InwardRawMaterialModel lot;

  const ConvertToWasteDialog({super.key, required this.lot});

  static Future<void> show(
    BuildContext context, {
    required InwardRawMaterialsCubit cubit,
    required InwardRawMaterialModel lot,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<InwardRawMaterialsCubit>.value(
        value: cubit,
        child: ConvertToWasteDialog(lot: lot),
      ),
    );
  }

  @override
  State<ConvertToWasteDialog> createState() => _ConvertToWasteDialogState();
}

class _ConvertToWasteDialogState extends State<ConvertToWasteDialog> {
  final TextEditingController _reasonController = TextEditingController();
  bool _isSubmitting = false;

  @override
  void dispose() {
    _reasonController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);

    final InwardRawMaterialsCubit cubit = context
        .read<InwardRawMaterialsCubit>();
    final waste = await cubit.convertToWaste(
      widget.lot.publicId,
      reason: _reasonController.text.trim(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (waste != null) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.INWARD_CONVERTED_TO_WASTE);
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
      icon: Icons.delete_sweep_outlined,
      title: AppStrings.INWARD_CONVERT_TO_WASTE,
      subtitle:
          '${widget.lot.productName} - ${widget.lot.lotNo}'
          '${widget.lot.farmerLabel.isEmpty ? '' : ' (${widget.lot.farmerLabel})'}',
      submitLabel: AppStrings.INWARD_CONVERT_TO_WASTE_ACTION,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.INWARD_CONVERT_TO_WASTE_BODY,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          AppTextField(
            controller: _reasonController,
            label: AppStrings.FIELD_REASON,
            hint: AppStrings.INWARD_CONVERT_TO_WASTE_REASON_HINT,
            enabled: !_isSubmitting,
            inputFormatters: [
              LengthLimitingTextInputFormatter(_REASON_MAX_LENGTH),
            ],
          ),
        ],
      ),
    );
  }
}
