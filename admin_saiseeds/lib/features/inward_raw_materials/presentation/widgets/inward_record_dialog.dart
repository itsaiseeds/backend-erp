import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/inward_raw_material_model.dart';
import '../bloc/inward_raw_materials_cubit.dart';
import 'inward_form_dialog.dart';

class InwardRecordDialog extends StatefulWidget {
  final InwardRawMaterialModel lot;
  final RecordDialogMode initialMode;

  const InwardRecordDialog({
    super.key,
    required this.lot,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    InwardRawMaterialModel lot, {
    required InwardRawMaterialsCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<InwardRawMaterialsCubit>.value(
        value: cubit,
        child: InwardRecordDialog(lot: lot, initialMode: initialMode),
      ),
    );
  }

  @override
  State<InwardRecordDialog> createState() => _InwardRecordDialogState();
}

class _InwardRecordDialogState extends State<InwardRecordDialog> {
  late final TextEditingController _productController;
  late final TextEditingController _partyController;
  late final TextEditingController _quantityController;

  late RecordDialogMode _mode;
  DateTime? _labSamplingDate;
  bool _markInUse = false;
  bool _isSubmitting = false;

  InwardRawMaterialModel get _lot => widget.lot;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _productController = TextEditingController(text: _lot.productName);
    _partyController = TextEditingController(text: _lot.partyName);
    _quantityController = TextEditingController(text: _lot.quantityKg);
    _labSamplingDate = _lot.labSamplingDateTime;
  }

  @override
  void dispose() {
    _productController.dispose();
    _partyController.dispose();
    _quantityController.dispose();
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    setState(() {
      _labSamplingDate = _lot.labSamplingDateTime;
      _markInUse = false;
      _mode = RecordDialogMode.view;
    });
  }

  void _notifyViewMode() {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: AppStrings.VIEW_MODE_TOAST_BODY,
    );
  }

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);

    final InwardRawMaterialsCubit cubit = context
        .read<InwardRawMaterialsCubit>();

    final bool succeeded = await cubit.updateLot(
      publicId: _lot.publicId,
      labSamplingDate: _labSamplingDate == null
          ? null
          : InwardFormDialog.isoDate.format(_labSamplingDate!),
      status: _markInUse ? InwardStatus.IN_USE : null,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.INWARD_UPDATED_TITLE);
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
      title: AppStrings.INWARD_DETAIL_TITLE,
      subtitle: _isEditing
          ? AppStrings.EDIT_INWARD_SUBTITLE
          : AppStrings.INWARD_DETAIL_SUBTITLE,
      mode: _mode,
      badge: AppBadge(
        label: _lot.isInUse
            ? AppStrings.STATUS_IN_USE
            : AppStrings.STATUS_LAB_TESTING,
        variant: _lot.isInUse
            ? AppBadgeVariant.success
            : AppBadgeVariant.warning,
      ),
      body: _buildFields(),
      onEdit: _enterEditMode,
      onCancelEdit: _cancelEdit,
      onSubmit: _isSubmitting ? null : _submit,
      isSubmitting: _isSubmitting,
      submitLabel: AppStrings.UPDATE,
    );
  }

  Widget _buildFields() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: RecordField(
            controller: _productController,
            label: AppStrings.COLUMN_PRODUCT,
            isEditable: false,
            isLocked: true,
          ),
          right: RecordField(
            controller: _partyController,
            label: AppStrings.COLUMN_PARTY,
            isEditable: false,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _quantityController,
            label: AppStrings.COLUMN_QUANTITY_KG,
            isEditable: false,
            isLocked: true,
          ),
          right: SingleDateField(
            value: _labSamplingDate,
            enabled: _canEdit,
            onBlockedTap: _notifyViewMode,
            onChanged: (date) => setState(() => _labSamplingDate = date),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _buildStatusSection(),
      ],
    );
  }

  Widget _buildStatusSection() {
    if (_lot.isInUse) {
      return _StatusNote(message: AppStrings.INWARD_STATUS_LOCKED_NOTE);
    }

    if (!_isEditing) {
      return const SizedBox.shrink();
    }

    return CheckboxListTile(
      value: _markInUse,
      onChanged: _isSubmitting
          ? null
          : (checked) => setState(() => _markInUse = checked ?? false),
      controlAffinity: ListTileControlAffinity.leading,
      contentPadding: EdgeInsets.zero,
      activeColor: AppColors.PRIMARY,
      title: Text(
        AppStrings.INWARD_MARK_IN_USE,
        style: AppTypography.bodyMedium,
      ),
    );
  }
}

class _StatusNote extends StatelessWidget {
  final String message;

  const _StatusNote({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.lock_outline_rounded,
            size: AppSizes.iconSm,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              message,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
