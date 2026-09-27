import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';

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
    return PopScope(
      canPop: !isSubmitting,
      child: SelectionContainer.disabled(
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
      ),
    );
  }

  Widget _buildDialog(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final double ceiling = (viewport.height - (AppSpacing.lg * 2)).clamp(
      0.0,
      AppSizes.dialogMaxHeight,
    );
    final double cardWidth = width.clamp(
      0.0,
      viewport.width - (AppSpacing.lg * 2),
    );

    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      insetPadding: const EdgeInsets.all(AppSpacing.lg),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: fixedHeight ?? ceiling,
          minHeight: fixedHeight ?? 0,
        ),
        child: Container(
          width: cardWidth,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.dialog),
            border: Border.all(color: AppColors.PRIMARY),
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
                isAccented: true,
                showClose: !isSubmitting,
                onClose: () => Navigator.of(context).pop(),
              ),
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
              Container(
                padding: const EdgeInsets.all(AppSpacing.lg),
                decoration: const BoxDecoration(
                  color: AppColors.BACKGROUND,
                  border: Border(top: BorderSide(color: AppColors.DIVIDER)),
                ),
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

class DialogHeaderAction extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;

  const DialogHeaderAction({
    super.key,
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onPressed,
        child: Tooltip(
          message: tooltip,
          child: SizedBox(
            width: AppSizes.dialogCloseTile,
            height: AppSizes.dialogCloseTile,
            child: Icon(icon, size: AppSizes.iconLg, color: AppColors.WHITE),
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
  final bool isAccented;
  final Widget? actionButton;
  final Widget? badge;
  final bool showClose;

  const AppDialogHeader({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onClose,
    this.isAccented = false,
    this.actionButton,
    this.badge,
    this.showClose = true,
  });

  Color get _titleColor =>
      isAccented ? AppColors.WHITE : AppColors.TEXT_PRIMARY;

  Color get _subtitleColor =>
      isAccented ? AppColors.SIDEBAR_ON_PRIMARY_MUTED : AppColors.TEXT_DISABLED;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: isAccented ? AppColors.PRIMARY : AppColors.SURFACE,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (isAccented)
            Icon(icon, size: AppSizes.iconXl, color: AppColors.WHITE)
          else
            Container(
              width: AppSizes.dialogIconTile,
              height: AppSizes.dialogIconTile,
              decoration: BoxDecoration(
                color: AppColors.PRIMARY_SURFACE,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              alignment: Alignment.center,
              child: Icon(
                icon,
                size: AppSizes.iconLg,
                color: AppColors.PRIMARY,
              ),
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
                    color: _titleColor,
                  ),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  subtitle,
                  style: AppTypography.bodySmall.copyWith(
                    color: _subtitleColor,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          if (badge != null) ...[
            badge!,
            const SizedBox(width: AppSpacing.smd),
          ],
          if (actionButton != null) ...[
            actionButton!,
            const SizedBox(width: AppSpacing.xs),
          ],
          if (showClose)
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
                      color: isAccented
                          ? AppColors.WHITE
                          : (onClose == null
                                ? AppColors.TEXT_DISABLED
                                : AppColors.TEXT_SECONDARY),
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
