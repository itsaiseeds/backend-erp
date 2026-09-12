import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

enum IconActionType { neutral, primary, success, warning, error }

class IconActionButton extends StatefulWidget {
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

  @override
  State<IconActionButton> createState() => _IconActionButtonState();
}

class _IconActionButtonState extends State<IconActionButton> {
  static const Duration _duration = Duration(milliseconds: 160);
  static const double _hoverOpacity = 0.08;

  bool _isHovered = false;

  Color get _color {
    switch (widget.type) {
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
    final bool isDisabled = widget.onPressed == null;
    final Color color = isDisabled ? AppColors.TEXT_DISABLED : _color;
    final bool isHot = _isHovered && !isDisabled;

    final Widget button = MouseRegion(
      cursor: isDisabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Padding(
        padding: EdgeInsets.all(widget.expand ? AppSizes.actionButtonInset : 0),
        child: GestureDetector(
          onTap: widget.onPressed,
          child: AnimatedContainer(
            duration: _duration,
            curve: Curves.easeOutCubic,
            width: widget.expand ? double.infinity : AppSpacing.xl,
            height: widget.expand ? double.infinity : AppSpacing.xl,
            decoration: BoxDecoration(
              color: isHot
                  ? color.withValues(alpha: _hoverOpacity)
                  : AppColors.TRANSPARENT,
              border: Border.all(color: isDisabled ? AppColors.BORDER : color),
              borderRadius: BorderRadius.circular(AppRadius.sm),
            ),
            alignment: Alignment.center,
            child: Icon(
              widget.icon,
              size: widget.expand ? AppSizes.iconLg : AppSpacing.md,
              color: color,
            ),
          ),
        ),
      ),
    );

    if (widget.tooltip == null || widget.tooltip!.isEmpty) return button;
    return Tooltip(message: widget.tooltip, child: button);
  }
}
