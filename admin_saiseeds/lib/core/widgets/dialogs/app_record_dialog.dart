import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../buttons/secondary_button.dart';
import '../layout/app_hairline.dart';
import 'app_form_dialog.dart';

enum RecordDialogMode { view, edit }

class RecordDialogAside {
  final String title;
  final String subtitle;
  final Widget child;

  const RecordDialogAside({
    required this.title,
    required this.subtitle,
    required this.child,
  });
}

class AppRecordDialog extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final RecordDialogMode mode;
  final Widget body;
  final RecordDialogAside? aside;
  final VoidCallback? onEdit;
  final VoidCallback? onCancelEdit;
  final VoidCallback? onSubmit;
  final String submitLabel;
  final String cancelLabel;
  final bool isSubmitting;
  final bool showFooterInViewMode;
  final bool isCancelEnabled;
  final bool isBodyFlush;
  final bool isTall;
  final double extraWidth;
  final double extraHeight;
  final Widget? badge;
  final Widget? headerBanner;

  const AppRecordDialog({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.mode,
    required this.body,
    this.aside,
    this.onEdit,
    this.onCancelEdit,
    this.onSubmit,
    this.submitLabel = AppStrings.UPDATE,
    this.cancelLabel = AppStrings.CANCEL,
    this.isSubmitting = false,
    this.showFooterInViewMode = false,
    this.isCancelEnabled = true,
    this.isBodyFlush = false,
    this.isTall = false,
    this.extraWidth = 0,
    this.extraHeight = 0,
    this.badge,
    this.headerBanner,
  });

  bool get _isEditing => mode == RecordDialogMode.edit;

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !isSubmitting,
      child: CallbackShortcuts(
        bindings: <ShortcutActivator, VoidCallback>{
          const SingleActivator(LogicalKeyboardKey.enter): _onEnter,
          const SingleActivator(LogicalKeyboardKey.numpadEnter): _onEnter,
        },
        child: Focus(autofocus: true, child: _buildDialog(context)),
      ),
    );
  }

  void _onEnter() {
    if (!_isEditing || isSubmitting) return;
    onSubmit?.call();
  }

  bool _showAside(double viewportWidth) =>
      aside != null && viewportWidth >= AppSizes.recordDialogAsideMinViewport;

  double _preferredWidth(double viewportWidth) {
    final double target =
        (_showAside(viewportWidth)
            ? AppSizes.recordDialogThreeColumnWidth
            : AppSizes.recordDialogTwoColumnWidth) +
        extraWidth;
    final double roomy = viewportWidth * AppSizes.recordDialogWidthFactor;
    final double available = viewportWidth - (AppSpacing.xxl * 2);
    return target.clamp(0.0, roomy.clamp(0.0, available));
  }

  Widget _buildDialog(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final bool showAside = _showAside(viewport.width);
    final double cardWidth = _preferredWidth(viewport.width);

    final double roomToGrow = viewport.height - (AppSpacing.xxl * 2);
    final double preferredHeight =
        viewport.height * AppSizes.recordDialogHeightFactor;
    final double ceiling = preferredHeight
        .clamp(0.0, AppSizes.dialogMaxHeight)
        .clamp(0.0, roomToGrow);
    final double trimmed = isTall
        ? ceiling
        : (ceiling - AppSizes.recordDialogHeightTrim).clamp(0.0, roomToGrow);
    final double maxHeight = (trimmed + extraHeight).clamp(0.0, roomToGrow);

    // Top-anchored: a footer appearing in edit mode must not shunt the whole
    // card downward the way a centred dialog would.
    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      alignment: Alignment.topCenter,
      insetPadding: const EdgeInsets.all(AppSpacing.xxl),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: maxHeight,
          maxWidth: cardWidth,
          minHeight: isBodyFlush ? maxHeight : 0,
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
            mainAxisSize: isBodyFlush ? MainAxisSize.max : MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              AppDialogHeader(
                icon: icon,
                title: title,
                subtitle: subtitle,
                isAccented: true,
                actionButton: _buildHeaderAction(),
                badge: badge,
                showClose: !isSubmitting,
                onClose: () => Navigator.of(context).pop(),
              ),
              ?headerBanner,
              if (isBodyFlush)
                Expanded(child: _buildBody(showAside))
              else
                Flexible(child: _buildBody(showAside)),
              if (_isEditing || showFooterInViewMode) _buildFooter(context),
            ],
          ),
        ),
      ),
    );
  }

  Widget? _buildHeaderAction() {
    if (_isEditing || onEdit == null) return null;
    return DialogHeaderAction(
      icon: Icons.edit_outlined,
      tooltip: AppStrings.EDIT,
      onPressed: onEdit!,
    );
  }

  Widget _buildBody(bool showAside) {
    if (!showAside) {
      if (isBodyFlush) return body;

      return SingleChildScrollView(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: body,
      );
    }

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Expanded(
          child: isBodyFlush
              ? body
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: body,
                ),
        ),
        const VerticalDivider(
          width: AppSizes.hairlineThickness,
          thickness: AppSizes.hairlineThickness,
          color: AppColors.HAIRLINE,
        ),
        SizedBox(
          width: AppSizes.recordDialogAsideWidth,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: _RecordAside(aside: aside!),
          ),
        ),
      ],
    );
  }

  Widget _buildFooter(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.BACKGROUND,
        border: Border(top: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        children: [
          if (onCancelEdit != null) ...[
            Expanded(
              child: SecondaryButton(
                label: cancelLabel,
                onPressed: isSubmitting || !isCancelEnabled
                    ? null
                    : onCancelEdit,
              ),
            ),
            const SizedBox(width: AppSpacing.md),
          ],
          Expanded(
            child: PrimaryButton(
              label: submitLabel,
              isLoading: isSubmitting,
              onPressed: onSubmit,
            ),
          ),
        ],
      ),
    );
  }
}

class _RecordAside extends StatelessWidget {
  final RecordDialogAside aside;

  const _RecordAside({required this.aside});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(aside.title, style: AppTypography.label),
        const SizedBox(height: AppSpacing.xxs),
        Text(aside.subtitle, style: AppTypography.bodySmall),
        const SizedBox(height: AppSpacing.md),
        const AppHairline(),
        const SizedBox(height: AppSpacing.md),
        aside.child,
      ],
    );
  }
}
