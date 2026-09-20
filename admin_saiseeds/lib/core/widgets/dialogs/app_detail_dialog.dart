import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../layout/app_hairline.dart';
import 'app_form_dialog.dart';

class AppDetailDialog extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Widget content;
  final double width;
  final Widget? footer;
  final double? fixedHeight;
  final bool isAccented;
  final Widget? headerAction;

  const AppDetailDialog({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.content,
    this.width = AppSizes.detailDialogWidth,
    this.footer,
    this.fixedHeight,
    this.isAccented = true,
    this.headerAction,
  });

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final double available = viewport.height - (AppSpacing.lg * 2);
    final double ceiling = available.clamp(0.0, AppSizes.dialogMaxHeight);
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
            border: Border.all(
              color: isAccented ? AppColors.PRIMARY : AppColors.BORDER,
            ),
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
                isAccented: isAccented,
                actionButton: headerAction,
                onClose: () => Navigator.of(context).pop(),
              ),
              if (!isAccented) const AppHairline(),
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
              if (footer != null)
                Container(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  decoration: const BoxDecoration(
                    color: AppColors.BACKGROUND,
                    border: Border(top: BorderSide(color: AppColors.DIVIDER)),
                  ),
                  child: footer,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
