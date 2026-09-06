import 'package:flutter/material.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import '../../../../core/config/observability_config.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/layout/app_surface_card.dart';

class LaunchingSoonPanel extends StatelessWidget {
  const LaunchingSoonPanel({super.key});

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      child: Center(
        child: SingleChildScrollView(
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: AppSizes.launchingSoonMaxWidth,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Container(
                  width: AppSizes.launchingSoonIconTile,
                  height: AppSizes.launchingSoonIconTile,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.PRIMARY_SURFACE,
                    borderRadius: BorderRadius.circular(AppRadius.lg),
                  ),
                  child: const Icon(
                    Icons.insights_outlined,
                    size: AppSizes.iconXxl,
                    color: AppColors.PRIMARY,
                  ),
                ),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  AppStrings.DASHBOARD_LAUNCHING_SOON_TITLE,
                  textAlign: TextAlign.center,
                  style: AppTypography.headingSmall,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  AppStrings.DASHBOARD_LAUNCHING_SOON_BODY,
                  textAlign: TextAlign.center,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
                if (ObservabilityConfig.isEnabled) ...[
                  const SizedBox(height: AppSpacing.lg),
                  SecondaryButton(
                    label: AppStrings.SENTRY_TEST_BUTTON,
                    icon: Icons.bug_report_outlined,
                    onPressed: () => _sendTestError(context),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _sendTestError(BuildContext context) async {
    try {
      throw Exception(AppStrings.SENTRY_TEST_EXCEPTION);
    } catch (error, stackTrace) {
      await Sentry.captureException(error, stackTrace: stackTrace);
    }
    if (!context.mounted) return;
    ToastUtils.showSuccess(
      context,
      AppStrings.SENTRY_TEST_SENT_TITLE,
      description: AppStrings.SENTRY_TEST_SENT_BODY,
    );
  }
}
