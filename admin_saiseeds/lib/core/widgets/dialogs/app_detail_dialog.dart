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

  const AppDetailDialog({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.content,
    this.width = AppSizes.detailDialogWidth,
    this.footer,
    this.fixedHeight,
  });

  @override
  Widget build(BuildContext context) {
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
                onClose: () => Navigator.of(context).pop(),
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
              if (footer != null) ...[
                const AppHairline(),
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: footer,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
