import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/responsive/responsive_helper.dart';

class SmallScreenGate extends StatelessWidget {
  final Widget child;

  const SmallScreenGate({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    if (!ResponsiveHelper.isMobile(context)) return child;
    return const SmallScreenNotice();
  }
}

class SmallScreenNotice extends StatelessWidget {
  const SmallScreenNotice({super.key});

  static const String _logoAsset = 'assets/logo/saiseeds-logo.png';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.BACKGROUND_TINTED,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                maxWidth: AppSizes.smallScreenNoticeWidth,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Image.asset(
                    _logoAsset,
                    height: AppSizes.smallScreenLogo,
                    fit: BoxFit.contain,
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Container(
                    width: AppSizes.smallScreenIconBox,
                    height: AppSizes.smallScreenIconBox,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: AppColors.PRIMARY_SURFACE,
                      borderRadius: BorderRadius.circular(AppRadius.lg),
                    ),
                    child: const Icon(
                      Icons.desktop_windows_outlined,
                      size: AppSizes.smallScreenIcon,
                      color: AppColors.PRIMARY,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                  Text(
                    AppStrings.SMALL_SCREEN_TITLE,
                    textAlign: TextAlign.center,
                    style: AppTypography.headingSmall,
                  ),
                  const SizedBox(height: AppSpacing.sm),
                  Text(
                    AppStrings.SMALL_SCREEN_BODY,
                    textAlign: TextAlign.center,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpacing.md,
                      vertical: AppSpacing.xs,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.SURFACE,
                      border: Border.all(color: AppColors.BORDER),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    child: Text(
                      AppStrings.SMALL_SCREEN_HINT,
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.TEXT_SECONDARY,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
