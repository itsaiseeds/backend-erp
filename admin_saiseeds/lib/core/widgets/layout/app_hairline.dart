import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

class AppHairline extends StatelessWidget {
  const AppHairline({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: AppSizes.hairlineThickness,
      color: AppColors.HAIRLINE,
    );
  }
}
