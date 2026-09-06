import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/constants/font_sizes.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import 'germination_motif_painter.dart';

class LoginBrandPanel extends StatelessWidget {
  final bool isCompact;

  const LoginBrandPanel({super.key, this.isCompact = false});

  static const double _logoHeightCompact = 48.0;
  static const double _logoHeightFull = 112.0;
  static const double _headlineMaxWidth = 420.0;
  static const double _ruleWidth = 48.0;
  static const double _ruleThickness = 2.0;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: AppColors.PRIMARY_DARK,
      child: Stack(
        fit: StackFit.expand,
        children: [
          const Positioned.fill(
            child: CustomPaint(painter: GerminationMotifPainter()),
          ),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isCompact ? AppSpacing.lg : AppSpacing.xxl,
              vertical: isCompact ? AppSpacing.lg : AppSpacing.xxl,
            ),
            child: isCompact ? _buildCompact() : _buildFull(),
          ),
        ],
      ),
    );
  }

  Widget _buildCompact() {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Image.asset(
          'assets/logo/saiseeds-logo.png',
          height: _logoHeightCompact,
          fit: BoxFit.contain,
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Text(
            AppStrings.LOGIN_BRAND_HEADLINE,
            style: AppTypography.titleMedium.copyWith(
              color: AppColors.TEXT_ON_PRIMARY,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFull() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Align(
          alignment: Alignment.topLeft,
          child: Image.asset(
            'assets/logo/saiseeds-logo.png',
            height: _logoHeightFull,
            fit: BoxFit.contain,
          ),
        ),
        const Spacer(),
        ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: _headlineMaxWidth),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                AppStrings.LOGIN_BRAND_HEADLINE,
                style: AppTypography.headingLarge.copyWith(
                  color: AppColors.TEXT_ON_PRIMARY,
                  height: 1.15,
                  letterSpacing: -0.5,
                ),
              ),
              const SizedBox(height: AppSpacing.lg),
              Container(
                width: _ruleWidth,
                height: _ruleThickness,
                color: AppColors.WHITE.withValues(alpha: 0.45),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                AppStrings.LOGIN_BRAND_TAGLINE,
                style: AppTypography.bodyLarge.copyWith(
                  color: AppColors.TEXT_ON_PRIMARY.withValues(alpha: 0.82),
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),
        const Spacer(),
        Text(
          AppStrings.LOGIN_BRAND_FOOTER,
          style: AppTypography.caption.copyWith(
            fontSize: AppFontSizes.FONT_12,
            color: AppColors.TEXT_ON_PRIMARY.withValues(alpha: 0.55),
            letterSpacing: 0.3,
          ),
        ),
      ],
    );
  }
}
