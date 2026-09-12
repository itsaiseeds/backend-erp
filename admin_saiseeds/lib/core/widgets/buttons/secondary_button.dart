import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../loaders/dots_loader.dart';

class SecondaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;

  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
  });

  bool get _isDisabled => onPressed == null || isLoading;

  @override
  Widget build(BuildContext context) {
    final Color foregroundColor = _isDisabled
        ? AppColors.TEXT_DISABLED
        : AppColors.PRIMARY;
    final Color borderColor = _isDisabled
        ? AppColors.BORDER
        : AppColors.PRIMARY;

    return MouseRegion(
      cursor: _isDisabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: OutlinedButton(
        onPressed: _isDisabled ? null : onPressed,
        style: OutlinedButton.styleFrom(
          foregroundColor: foregroundColor,
          disabledForegroundColor: foregroundColor,
          side: BorderSide(color: borderColor),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.lg,
            vertical: AppSpacing.sm,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
        ),
        child: isLoading
            ? SizedBox(
                height: AppSpacing.md,
                child: DotsLoader(color: foregroundColor),
              )
            : Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: AppSpacing.md),
                    const SizedBox(width: AppSpacing.sm),
                  ],
                  Text(
                    label,
                    style: AppTypography.button.copyWith(
                      color: foregroundColor,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
