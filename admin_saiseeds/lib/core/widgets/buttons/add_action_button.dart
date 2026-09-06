import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

class AddActionButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final String tooltip;

  const AddActionButton({
    super.key,
    required this.onPressed,
    required this.tooltip,
  });

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = onPressed == null;

    return Tooltip(
      message: tooltip,
      child: MouseRegion(
        cursor: isDisabled
            ? SystemMouseCursors.basic
            : SystemMouseCursors.click,
        child: Padding(
          padding: const EdgeInsets.all(AppSizes.actionButtonInset),
          child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(AppRadius.md),
          child: Container(
            decoration: BoxDecoration(
              color: isDisabled ? AppColors.SURFACE_VARIANT : AppColors.PRIMARY,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            alignment: Alignment.center,
            child: Icon(
              Icons.add_rounded,
              size: AppSizes.iconLg,
              color: isDisabled
                  ? AppColors.TEXT_DISABLED
                  : AppColors.TEXT_ON_PRIMARY,
            ),
          ),
        ),
        ),
      ),
    );
  }
}
