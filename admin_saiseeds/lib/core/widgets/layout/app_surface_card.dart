import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

class AppSurfaceCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;

  const AppSurfaceCard({super.key, required this.child, this.padding});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.fromBorderSide(
          BorderSide(color: AppColors.BORDER, width: AppSizes.borderThin),
        ),
        borderRadius: BorderRadius.all(Radius.circular(AppRadius.lg)),
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(AppSpacing.lg),
        child: child,
      ),
    );
  }
}
