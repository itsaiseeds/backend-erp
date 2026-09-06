import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../buttons/secondary_button.dart';
import '../dialogs/app_dialog_shell.dart';

class ConfirmationDialog extends StatelessWidget {
  final String title;
  final String message;
  final String confirmLabel;
  final String cancelLabel;
  final bool isDangerous;

  const ConfirmationDialog({
    super.key,
    required this.title,
    required this.message,
    this.confirmLabel = AppStrings.CONFIRM,
    this.cancelLabel = AppStrings.CANCEL,
    this.isDangerous = false,
  });

  static Future<bool> show(
    BuildContext context, {
    required String title,
    required String message,
    String confirmLabel = AppStrings.CONFIRM,
    String cancelLabel = AppStrings.CANCEL,
    bool isDangerous = false,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (context) => ConfirmationDialog(
        title: title,
        message: message,
        confirmLabel: confirmLabel,
        cancelLabel: cancelLabel,
        isDangerous: isDangerous,
      ),
    );
    return result ?? false;
  }

  @override
  Widget build(BuildContext context) {
    return AppDialogShell(
      title: title,
      showCloseButton: false,
      content: Text(message, style: AppTypography.bodyMedium),
      actions: [
        SecondaryButton(
          label: cancelLabel,
          onPressed: () => Navigator.of(context).pop(false),
        ),
        PrimaryButton(
          label: confirmLabel,
          isDangerous: isDangerous,
          onPressed: () => Navigator.of(context).pop(true),
        ),
      ],
    );
  }
}
