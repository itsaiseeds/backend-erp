import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../buttons/secondary_button.dart';
import '../dialogs/app_dialog_shell.dart';

class _ConfirmIntent extends Intent {
  const _ConfirmIntent();
}

class ConfirmationDialog extends StatelessWidget {
  final String title;
  final String message;
  final String confirmLabel;
  final String cancelLabel;
  final bool isDangerous;
  final bool isAlert;

  const ConfirmationDialog({
    super.key,
    required this.title,
    required this.message,
    this.confirmLabel = AppStrings.CONFIRM,
    this.cancelLabel = AppStrings.CANCEL,
    this.isDangerous = false,
    this.isAlert = false,
  });

  static Future<bool> show(
    BuildContext context, {
    required String title,
    required String message,
    String confirmLabel = AppStrings.CONFIRM,
    String cancelLabel = AppStrings.CANCEL,
    bool isDangerous = false,
  }) async {
    final bool? result = await showDialog<bool>(
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

  static Future<void> showAlert(
    BuildContext context, {
    required String title,
    required String message,
    bool isDangerous = false,
  }) {
    return showDialog<void>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (context) => ConfirmationDialog(
        title: title,
        message: message,
        isDangerous: isDangerous,
        isAlert: true,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Shortcuts(
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.enter): _ConfirmIntent(),
        SingleActivator(LogicalKeyboardKey.numpadEnter): _ConfirmIntent(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _ConfirmIntent: CallbackAction<_ConfirmIntent>(
            onInvoke: (intent) {
              Navigator.of(context).pop(true);
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: AppDialogShell(
            title: title,
            tone: isDangerous
                ? DialogHeaderTone.danger
                : DialogHeaderTone.primary,
            icon: isDangerous
                ? Icons.warning_amber_rounded
                : Icons.info_outline_rounded,
            showCloseButton: false,
            content: Text(message, style: AppTypography.bodyMedium),
            actions: [
              if (!isAlert)
                SecondaryButton(
                  label: cancelLabel,
                  onPressed: () => Navigator.of(context).pop(false),
                ),
              PrimaryButton(
                label: isAlert ? AppStrings.OK : confirmLabel,
                isDangerous: isDangerous,
                onPressed: () => Navigator.of(context).pop(true),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
