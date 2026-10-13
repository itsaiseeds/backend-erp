import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../buttons/secondary_button.dart';
import '../dialogs/app_dialog_shell.dart';
import '../inputs/app_toggle_field.dart';

/// The "are you sure" dialog shown before a bag/packet stock count is
/// recorded, with a "reuse other material" toggle alongside it: a lower
/// count feeds the removed stock back into the other material pool unless
/// the admin explicitly turns this off.
///
/// On by default -- that is the safe outcome for a routine same/higher count
/// submission, where nothing is actually being reused. It only matters, and
/// needs a deliberate uncheck, when a product's count is genuinely going
/// down.
class StockUpdateConfirmDialog extends StatefulWidget {
  const StockUpdateConfirmDialog({super.key});

  /// Resolves to `null` if cancelled, or the chosen "reuse other material"
  /// value if confirmed.
  static Future<bool?> show(BuildContext context) {
    return showDialog<bool>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (_) => const StockUpdateConfirmDialog(),
    );
  }

  @override
  State<StockUpdateConfirmDialog> createState() =>
      _StockUpdateConfirmDialogState();
}

class _StockUpdateConfirmDialogState extends State<StockUpdateConfirmDialog> {
  bool _reuseOtherMaterial = true;

  @override
  Widget build(BuildContext context) {
    return AppDialogShell(
      title: AppStrings.STOCK_CONFIRM_TITLE,
      tone: DialogHeaderTone.primary,
      icon: Icons.info_outline_rounded,
      showCloseButton: false,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(AppStrings.STOCK_CONFIRM_BODY, style: AppTypography.bodyMedium),
          const SizedBox(height: AppSpacing.md),
          Container(
            padding: const EdgeInsets.all(AppSpacing.smd),
            decoration: BoxDecoration(
              color: AppColors.WARNING_LIGHT,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.WARNING),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.warning_amber_rounded,
                  size: AppSizes.iconSm,
                  color: AppColors.WARNING,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    AppStrings.STOCK_CONFIRM_DECREASE_HINT,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_PRIMARY,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          AppToggleField(
            label: AppStrings.STOCK_REUSE_OTHER_MATERIAL,
            value: _reuseOtherMaterial,
            onChanged: (bool value) =>
                setState(() => _reuseOtherMaterial = value),
          ),
        ],
      ),
      actions: [
        SecondaryButton(
          label: AppStrings.CANCEL,
          onPressed: () => Navigator.of(context).pop(),
        ),
        PrimaryButton(
          label: AppStrings.STOCK_CONFIRM_ACTION,
          onPressed: () => Navigator.of(context).pop(_reuseOtherMaterial),
        ),
      ],
    );
  }
}
