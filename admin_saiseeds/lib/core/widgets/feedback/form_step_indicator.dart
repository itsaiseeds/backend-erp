import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class FormStepIndicator extends StatelessWidget {
  final List<String> labels;
  final int currentIndex;
  final ValueChanged<int>? onStepTapped;

  const FormStepIndicator({
    super.key,
    required this.labels,
    required this.currentIndex,
    this.onStepTapped,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (int index = 0; index < labels.length; index++) ...[
          if (index > 0)
            Expanded(
              child: Container(
                height: AppSizes.borderThin,
                margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
                color: index <= currentIndex
                    ? AppColors.PRIMARY
                    : AppColors.BORDER,
              ),
            ),
          _StepDot(
            index: index,
            label: labels[index],
            isActive: index == currentIndex,
            isComplete: index < currentIndex,
            onTap: onStepTapped == null ? null : () => onStepTapped!(index),
          ),
        ],
      ],
    );
  }
}

class _StepDot extends StatelessWidget {
  static const Duration _duration = Duration(milliseconds: 200);

  final int index;
  final String label;
  final bool isActive;
  final bool isComplete;
  final VoidCallback? onTap;

  const _StepDot({
    required this.index,
    required this.label,
    required this.isActive,
    required this.isComplete,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isHighlighted = isActive || isComplete;

    return GestureDetector(
      onTap: onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedContainer(
            duration: _duration,
            curve: Curves.easeOutCubic,
            width: AppSizes.stepDotSize,
            height: AppSizes.stepDotSize,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isHighlighted ? AppColors.PRIMARY : AppColors.SURFACE,
              border: Border.all(
                color: isHighlighted ? AppColors.PRIMARY : AppColors.BORDER,
              ),
            ),
            child: isComplete
                ? const Icon(
                    Icons.check_rounded,
                    size: AppSizes.iconSm,
                    color: AppColors.TEXT_ON_PRIMARY,
                  )
                : Text(
                    '${index + 1}',
                    style: AppTypography.labelMedium.copyWith(
                      color: isHighlighted
                          ? AppColors.TEXT_ON_PRIMARY
                          : AppColors.TEXT_SECONDARY,
                    ),
                  ),
          ),
          const SizedBox(height: AppSpacing.xxs),
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: isHighlighted
                  ? AppColors.TEXT_PRIMARY
                  : AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ),
    );
  }
}
