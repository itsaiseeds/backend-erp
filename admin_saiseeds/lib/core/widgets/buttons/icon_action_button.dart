import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

enum IconActionType { neutral, primary, success, warning, error }

class IconActionButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onPressed;
  final String? tooltip;
  final IconActionType type;
  final bool expand;

  const IconActionButton({
    super.key,
    required this.icon,
    required this.onPressed,
    this.tooltip,
    this.type = IconActionType.neutral,
    this.expand = false,
  });

  Color get _color {
    switch (type) {
      case IconActionType.primary:
        return AppColors.PRIMARY;
      case IconActionType.success:
        return AppColors.SUCCESS;
      case IconActionType.warning:
        return AppColors.WARNING;
      case IconActionType.error:
        return AppColors.ERROR;
      case IconActionType.neutral:
        return AppColors.TEXT_SECONDARY;
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = onPressed == null;
    final Color color = isDisabled ? AppColors.TEXT_DISABLED : _color;

    final Widget button = MouseRegion(
      cursor: isDisabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: Padding(
        padding: EdgeInsets.all(
          expand ? AppSizes.actionButtonInset : 0,
        ),
        child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Container(
          width: expand ? double.infinity : AppSpacing.xl,
          height: expand ? double.infinity : AppSpacing.xl,
          decoration: BoxDecoration(
            border: Border.all(color: isDisabled ? AppColors.BORDER : color),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          alignment: Alignment.center,
          child: Icon(
            icon,
            size: expand ? AppSizes.iconLg : AppSpacing.md,
            color: color,
          ),
        ),
        ),
      ),
    );

    if (tooltip == null || tooltip!.isEmpty) return button;
    return Tooltip(message: tooltip, child: button);
  }
}
