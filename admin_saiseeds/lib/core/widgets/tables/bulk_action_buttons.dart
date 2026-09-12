import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/toast_utils.dart';
import '../feedback/confirmation_dialog.dart';

class BulkActionButtons extends StatefulWidget {
  final ValueListenable<Map<String, String>> selectionListenable;
  final Future<bool> Function(String id)? onDeleteItem;
  final VoidCallback? onComplete;

  const BulkActionButtons({
    super.key,
    required this.selectionListenable,
    this.onDeleteItem,
    this.onComplete,
  });

  @override
  State<BulkActionButtons> createState() => _BulkActionButtonsState();
}

class _BulkActionButtonsState extends State<BulkActionButtons> {
  bool _isDeleting = false;

  Future<void> _confirmAndDelete(Map<String, String> selection) async {
    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.TABLE_BULK_DELETE_TITLE,
      message: AppStrings.TABLE_BULK_DELETE_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed || !mounted) return;

    setState(() => _isDeleting = true);
    int failures = 0;
    for (final id in selection.keys) {
      try {
        final bool success = await widget.onDeleteItem!(id);
        if (!success) failures++;
      } catch (_) {
        failures++;
      }
    }
    if (!mounted) return;
    setState(() => _isDeleting = false);

    if (failures > 0) {
      ToastUtils.showError(
        context,
        AppStrings.TABLE_BULK_DELETE_FAILED_TITLE,
        description: AppStrings.TABLE_BULK_DELETE_FAILED_BODY,
      );
    } else {
      ToastUtils.showSuccess(context, AppStrings.TABLE_BULK_DELETE_DONE_TITLE);
    }
    widget.onComplete?.call();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.onDeleteItem == null) return const SizedBox.shrink();

    return ValueListenableBuilder<Map<String, String>>(
      valueListenable: widget.selectionListenable,
      builder: (context, selection, _) {
        if (selection.isEmpty) return const SizedBox.shrink();
        return OutlinedButton.icon(
          onPressed: _isDeleting ? null : () => _confirmAndDelete(selection),
          icon: const Icon(Icons.delete_outline_rounded, size: AppSizes.iconSm),
          label: Text(
            '${AppStrings.TABLE_BULK_DELETE} (${selection.length})',
            style: AppTypography.labelMedium.copyWith(color: AppColors.ERROR),
          ),
          style: OutlinedButton.styleFrom(
            foregroundColor: AppColors.ERROR,
            disabledForegroundColor: AppColors.TEXT_DISABLED,
            side: const BorderSide(color: AppColors.ERROR),
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.md,
              vertical: AppSpacing.sm,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
          ),
        );
      },
    );
  }
}
