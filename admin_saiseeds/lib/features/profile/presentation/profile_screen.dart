import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters/role_formatter.dart';
import '../../../core/widgets/buttons/secondary_button.dart';
import '../../../core/widgets/feedback/app_badge.dart';
import '../../../core/widgets/feedback/empty_state.dart';
import '../../../core/widgets/layout/app_hairline.dart';
import '../../../core/widgets/loaders/shimmer_rows.dart';
import '../../auth/data/models/auth_session.dart';
import '../../auth/presentation/bloc/session_cubit.dart';
import '../../auth/presentation/logout_action.dart';
import 'widgets/profile_permission_row.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SessionCubit, SessionState>(
      builder: (context, state) {
        switch (state.status) {
          case SessionStatus.loading:
            return const Padding(
              padding: EdgeInsets.all(AppSpacing.lg),
              child: ShimmerRows(rowCount: 4, rowHeight: AppSpacing.lgs),
            );
          case SessionStatus.absent:
            return const EmptyState(
              icon: Icons.person_off_outlined,
              title: AppStrings.PROFILE_UNAVAILABLE_TITLE,
              subtitle: AppStrings.PROFILE_UNAVAILABLE_BODY,
            );
          case SessionStatus.loaded:
            return _ProfileContent(session: state.session!);
        }
      },
    );
  }
}

class _ProfileContent extends StatelessWidget {
  final AuthSession session;

  const _ProfileContent({required this.session});

  String get _displayName =>
      session.name.isEmpty ? AppStrings.PROFILE_VALUE_UNKNOWN : session.name;

  String get _displayPhone => session.phoneNumber.isEmpty
      ? AppStrings.PROFILE_VALUE_UNKNOWN
      : session.phoneNumber;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(
            maxWidth: AppSizes.profileContentMaxWidth,
          ),
          child: DecoratedBox(
            decoration: const BoxDecoration(
              color: AppColors.SURFACE,
              border: Border.fromBorderSide(
                BorderSide(color: AppColors.BORDER),
              ),
              borderRadius: BorderRadius.all(Radius.circular(AppRadius.lg)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                _Identity(
                  name: _displayName,
                  phone: _displayPhone,
                  role: RoleFormatter.label(session.role),
                ),
                const AppHairline(),
                Padding(
                  padding: const EdgeInsets.all(AppSpacing.lg),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        AppStrings.PROFILE_PERMISSIONS,
                        style: AppTypography.titleMedium,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      ProfilePermissionRow(
                        label: AppStrings.PROFILE_PERMISSION_CREATE_ADMIN,
                        description:
                            AppStrings.PROFILE_PERMISSION_CREATE_ADMIN_HINT,
                        icon: Icons.admin_panel_settings_outlined,
                        isGranted: session.canCreateAdmin,
                      ),
                      const AppHairline(),
                      ProfilePermissionRow(
                        label:
                            AppStrings.PROFILE_PERMISSION_CREATE_SALES_PERSON,
                        description: AppStrings
                            .PROFILE_PERMISSION_CREATE_SALES_PERSON_HINT,
                        icon: Icons.groups_outlined,
                        isGranted: session.canCreateSalesPerson,
                      ),
                    ],
                  ),
                ),
                const AppHairline(),
                _SessionFooter(onLogout: () => LogoutAction.run(context)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Identity extends StatelessWidget {
  final String name;
  final String phone;
  final String role;

  const _Identity({
    required this.name,
    required this.phone,
    required this.role,
  });

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: AppColors.PRIMARY_SURFACE,
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              AppStrings.PROFILE_SIGNED_IN_AS,
              style: AppTypography.overline.copyWith(color: AppColors.PRIMARY),
            ),
            const SizedBox(height: AppSpacing.sm),
            Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Flexible(
                  child: Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.headingSmall,
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                const Icon(
                  Icons.phone_outlined,
                  size: AppSizes.iconSm,
                  color: AppColors.TEXT_SECONDARY,
                ),
                const SizedBox(width: AppSpacing.xs),
                Flexible(
                  child: Text(
                    phone,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.md),
                AppBadge(label: role, variant: AppBadgeVariant.success),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _SessionFooter extends StatelessWidget {
  final VoidCallback onLogout;

  const _SessionFooter({required this.onLogout});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        children: [
          Expanded(
            child: Text(
              AppStrings.PROFILE_SESSION_SIGN_OUT_HINT,
              style: AppTypography.caption,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          SecondaryButton(
            label: AppStrings.LOGOUT,
            icon: Icons.logout_rounded,
            onPressed: onLogout,
          ),
        ],
      ),
    );
  }
}
