import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/widgets/feedback/empty_state.dart';
import '../../../../core/widgets/layout/app_surface_card.dart';
import '../../../../core/widgets/layout/page_header.dart';

class AdminsView extends StatelessWidget {
  const AdminsView({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PageHeader(
            eyebrow: AppStrings.SIDEBAR_NAVIGATION,
            title: AppStrings.ADMINS,
            subtitle: AppStrings.ADMINS_EMPTY_BODY,
          ),
          const SizedBox(height: AppSpacing.lg),
          const Expanded(
            child: AppSurfaceCard(
              child: EmptyState(
                icon: Icons.admin_panel_settings_outlined,
                title: AppStrings.ADMINS_EMPTY_TITLE,
                subtitle: AppStrings.ADMINS_EMPTY_BODY,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
