import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

enum OutlinedActionTone { primary, error }

class OutlinedActionButton extends StatefulWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final OutlinedActionTone tone;

  const OutlinedActionButton({
    super.key,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.tone = OutlinedActionTone.primary,
  });

  @override
  State<OutlinedActionButton> createState() => _OutlinedActionButtonState();
}

class _OutlinedActionButtonState extends State<OutlinedActionButton> {
  static const Duration _duration = Duration(milliseconds: 160);
  static const double _hoverOpacity = 0.08;

  bool _isHovered = false;

  Color get _accent => widget.tone == OutlinedActionTone.primary
      ? AppColors.PRIMARY
      : AppColors.ERROR;

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = widget.onPressed == null;
    final Color accent = isDisabled ? AppColors.TEXT_DISABLED : _accent;
    final bool isHot = _isHovered && !isDisabled;

    return MouseRegion(
      cursor: isDisabled
          ? SystemMouseCursors.basic
          : SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: _duration,
          curve: Curves.easeOutCubic,
          height: AppSizes.tableActionButtonHeight,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
          decoration: BoxDecoration(
            color: isHot
                ? accent.withValues(alpha: _hoverOpacity)
                : AppColors.TRANSPARENT,
            border: Border.all(color: accent),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(widget.icon, size: AppSizes.iconSm, color: accent),
              const SizedBox(width: AppSpacing.xs),
              Text(
                widget.label,
                style: AppTypography.labelSmall.copyWith(color: accent),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
