import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppDialogShell extends StatelessWidget {
  final String title;
  final Widget content;
  final List<Widget>? actions;
  final double width;
  final bool showCloseButton;

  const AppDialogShell({
    super.key,
    required this.title,
    required this.content,
    this.actions,
    this.width = 420,
    this.showCloseButton = true,
  });

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.all(AppSpacing.lg),
      child: Container(
        width: width,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          color: AppColors.SURFACE,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppColors.BORDER),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.lg,
                vertical: AppSpacing.md,
              ),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.DIVIDER)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(title, style: AppTypography.titleMedium),
                  ),
                  if (showCloseButton)
                    MouseRegion(
                      cursor: SystemMouseCursors.click,
                      child: IconButton(
                        icon: const Icon(
                          Icons.close_rounded,
                          color: AppColors.TEXT_SECONDARY,
                        ),
                        onPressed: () => Navigator.of(context).pop(),
                        splashRadius: AppSpacing.md,
                      ),
                    ),
                ],
              ),
            ),
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
}
