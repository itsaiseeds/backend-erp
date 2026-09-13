import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../layout/app_hairline.dart';

class AppFormDialog extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget content;
  final String submitLabel;
  final VoidCallback? onSubmit;
  final bool isSubmitting;
  final double width;
  final Widget? leadingAction;
  final double? fixedHeight;

  const AppFormDialog({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.content,
    required this.submitLabel,
    required this.onSubmit,
    this.isSubmitting = false,
    this.width = AppSizes.formDialogWidth,
    this.leadingAction,
    this.fixedHeight,
  });

  @override
  Widget build(BuildContext context) {
    // Enter advances or submits, whichever the form's onSubmit currently means.
    // A disabled onSubmit (mid-request) leaves the key unhandled.
    return SelectionContainer.disabled(
      child: CallbackShortcuts(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(LogicalKeyboardKey.enter): () {
            if (isSubmitting) return;
            onSubmit?.call();
          },
          const SingleActivator(LogicalKeyboardKey.numpadEnter): () {
            if (isSubmitting) return;
            onSubmit?.call();
          },
        },
        child: Focus(autofocus: true, child: _buildDialog(context)),
      ),
    );
  }

  Widget _buildDialog(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      insetPadding: const EdgeInsets.all(AppSpacing.lg),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: fixedHeight ?? AppSizes.dialogMaxHeight,
          minHeight: fixedHeight ?? 0,
        ),
        child: Container(
          width: width,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(color: AppColors.BORDER),
          ),
          child: Column(
            mainAxisSize: fixedHeight == null
                ? MainAxisSize.min
                : MainAxisSize.max,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppDialogHeader(
                icon: icon,
                title: title,
                subtitle: subtitle,
                onClose: isSubmitting
                    ? null
                    : () => Navigator.of(context).pop(),
              ),
              const AppHairline(),
              if (fixedHeight == null)
                Flexible(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: content,
                  ),
                )
              else
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(AppSpacing.lg),
                    child: content,
                  ),
                ),
              const AppHairline(),
              Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: Row(
                  children: [
                    if (leadingAction != null) ...[
                      Expanded(child: leadingAction!),
                      const SizedBox(width: AppSpacing.md),
                    ],
                    Expanded(
                      flex: leadingAction == null ? 1 : 2,
                      child: PrimaryButton(
                        label: submitLabel,
                        isLoading: isSubmitting,
                        onPressed: onSubmit,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class AppDialogHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onClose;

  const AppDialogHeader({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: AppSizes.dialogIconTile,
            height: AppSizes.dialogIconTile,
            decoration: BoxDecoration(
              color: AppColors.PRIMARY_SURFACE,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            alignment: Alignment.center,
            child: Icon(icon, size: AppSizes.iconLg, color: AppColors.PRIMARY),
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.titleMedium.copyWith(
                    letterSpacing: -0.2,
                  ),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  subtitle,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_DISABLED,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          MouseRegion(
            cursor: onClose == null
                ? SystemMouseCursors.basic
                : SystemMouseCursors.click,
            child: GestureDetector(
              onTap: onClose,
              child: Tooltip(
                message: AppStrings.CLOSE,
                child: SizedBox(
                  width: AppSizes.dialogCloseTile,
                  height: AppSizes.dialogCloseTile,
                  child: Icon(
                    Icons.close_rounded,
                    size: AppSizes.iconLg,
                    color: onClose == null
                        ? AppColors.TEXT_DISABLED
                        : AppColors.TEXT_SECONDARY,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
