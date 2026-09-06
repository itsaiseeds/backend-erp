import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/layout/app_surface_card.dart';
import '../../../../core/widgets/layout/page_header.dart';
import '../../../auth/presentation/bloc/session_cubit.dart';
import '../widgets/dashboard_stat_tile.dart';

class DashboardOverviewView extends StatelessWidget {
  const DashboardOverviewView({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const PageHeader(
            eyebrow: AppStrings.LOGIN_EYEBROW,
            title: AppStrings.DASHBOARD_OVERVIEW_TITLE,
            subtitle: AppStrings.DASHBOARD_OVERVIEW_SUBTITLE,
          ),
          const SizedBox(height: AppSpacing.lg),
          BlocBuilder<SessionCubit, SessionState>(
            builder: (context, state) {
              final name = state.session?.name ?? '';
              return _StatGrid(
                sessionCaption: name.isEmpty
                    ? AppStrings.DASHBOARD_STAT_SIGNED_IN
                    : name,
              );
            },
          ),
          const SizedBox(height: AppSpacing.lg),
          const _PendingDataNotice(),
        ],
      ),
    );
  }
}

class _StatGrid extends StatelessWidget {
  final String sessionCaption;

  const _StatGrid({required this.sessionCaption});

  @override
  Widget build(BuildContext context) {
    final tiles = <Widget>[
      const DashboardStatTile(
        icon: Icons.admin_panel_settings_outlined,
        label: AppStrings.DASHBOARD_STAT_ADMINS,
        value: AppStrings.DASHBOARD_STAT_PLACEHOLDER,
        caption: AppStrings.DASHBOARD_STAT_NOT_WIRED,
      ),
      const DashboardStatTile(
        icon: Icons.groups_outlined,
        label: AppStrings.DASHBOARD_STAT_SALES_PEOPLE,
        value: AppStrings.DASHBOARD_STAT_PLACEHOLDER,
        caption: AppStrings.DASHBOARD_STAT_NOT_WIRED,
      ),
      DashboardStatTile(
        icon: Icons.verified_user_outlined,
        label: AppStrings.DASHBOARD_STAT_ACTIVE_SESSION,
        value: AppStrings.DASHBOARD_STAT_SIGNED_IN,
        caption: sessionCaption,
        isAccented: true,
      ),
      const DashboardStatTile(
        icon: Icons.insights_outlined,
        label: AppStrings.DASHBOARD_STAT_PENDING,
        value: AppStrings.DASHBOARD_STAT_PLACEHOLDER,
        caption: AppStrings.DASHBOARD_STAT_NOT_WIRED,
      ),
    ];

    return LayoutBuilder(
      builder: (context, constraints) {
        final int columns = _columnsFor(constraints.maxWidth);
        final double gap = AppSpacing.md;
        final double tileWidth =
            (constraints.maxWidth - gap * (columns - 1)) / columns;

        return Wrap(
          spacing: gap,
          runSpacing: gap,
          children: tiles
              .map(
                (tile) => SizedBox(
                  width: tileWidth > 0 ? tileWidth : constraints.maxWidth,
                  child: tile,
                ),
              )
              .toList(),
        );
      },
    );
  }

  int _columnsFor(double width) {
    final int fit = (width / AppSizes.statTileMinWidth).floor();
    if (fit >= 4) return 4;
    if (fit >= 2) return 2;
    return 1;
  }
}

class _PendingDataNotice extends StatelessWidget {
  const _PendingDataNotice();

  @override
  Widget build(BuildContext context) {
    return AppSurfaceCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.info_outline_rounded,
            size: AppSizes.iconLg,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.DASHBOARD_NOTICE_TITLE,
                  style: AppTypography.label,
                ),
                const SizedBox(height: AppSpacing.xs),
                Text(
                  AppStrings.DASHBOARD_NOTICE_BODY,
                  style: AppTypography.bodySmall,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
