import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

enum DialogHeaderTone { plain, primary, danger }

class AppDialogShell extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget content;
  final List<Widget>? actions;
  final double width;
  final bool showCloseButton;
  final DialogHeaderTone tone;
  final IconData? icon;

  const AppDialogShell({
    super.key,
    required this.title,
    required this.content,
    this.subtitle,
    this.actions,
    this.width = AppSizes.confirmDialogWidth,
    this.showCloseButton = true,
    this.tone = DialogHeaderTone.plain,
    this.icon,
  });

  bool get _isAccented => tone != DialogHeaderTone.plain;

  Color get _accent =>
      tone == DialogHeaderTone.danger ? AppColors.ERROR : AppColors.PRIMARY;

  Color get _titleColor =>
      _isAccented ? AppColors.WHITE : AppColors.TEXT_PRIMARY;

  Color get _subtitleColor =>
      _isAccented ? AppColors.WHITE : AppColors.TEXT_SECONDARY;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      insetPadding: const EdgeInsets.all(AppSpacing.lg),
      child: Container(
        width: width,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: AppColors.SURFACE,
          borderRadius: BorderRadius.circular(AppRadius.dialog),
          border: Border.all(
            color: _isAccented ? _accent : AppColors.BORDER,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _buildHeader(context),
            Flexible(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.lg),
                child: content,
              ),
            ),
            if (actions != null && actions!.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                  vertical: AppSpacing.md,
                ),
                decoration: const BoxDecoration(
                  color: AppColors.BACKGROUND,
                  border: Border(top: BorderSide(color: AppColors.DIVIDER)),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    for (int i = 0; i < actions!.length; i++) ...[
                      if (i > 0) const SizedBox(width: AppSpacing.sm),
                      actions![i],
                    ],
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    final String? caption = subtitle;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      decoration: BoxDecoration(
        color: _isAccented ? _accent : AppColors.SURFACE,
        border: const Border(bottom: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        children: [
          if (icon != null) ...[
            if (_isAccented)
              Icon(icon, size: AppSizes.iconXl, color: AppColors.WHITE)
            else
              Container(
                width: AppSizes.dialogHeaderIconBox,
                height: AppSizes.dialogHeaderIconBox,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: tone == DialogHeaderTone.danger
                      ? AppColors.ERROR_LIGHT
                      : AppColors.PRIMARY_SURFACE,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Icon(icon, size: AppSizes.iconMd, color: _accent),
              ),
            const SizedBox(width: AppSpacing.smd),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: AppTypography.titleMedium.copyWith(color: _titleColor),
                ),
                if (caption != null && caption.trim().isNotEmpty) ...[
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    caption,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodySmall.copyWith(
                      color: _subtitleColor,
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (showCloseButton)
            MouseRegion(
              cursor: SystemMouseCursors.click,
              child: IconButton(
                icon: Icon(
                  Icons.close_rounded,
                  color: _isAccented
                      ? AppColors.WHITE
                      : AppColors.TEXT_SECONDARY,
                ),
                onPressed: () => Navigator.of(context).pop(),
                splashRadius: AppSpacing.md,
              ),
            ),
        ],
      ),
    );
  }
}
