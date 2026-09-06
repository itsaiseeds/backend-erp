import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_spacing.dart';
import '../../../core/theme/app_typography.dart';
import '../../../core/utils/formatters/role_formatter.dart';
import '../../../core/widgets/buttons/secondary_button.dart';
import '../../../core/widgets/feedback/empty_state.dart';
import '../../../core/widgets/loaders/shimmer_rows.dart';
import '../../auth/data/models/auth_session.dart';
import '../../auth/presentation/bloc/session_cubit.dart';
import '../../auth/presentation/logout_action.dart';
import 'widgets/profile_detail_field.dart';
import 'widgets/profile_identity_card.dart';
import 'widgets/profile_permission_row.dart';
import 'widgets/profile_section.dart';

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

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isCompact =
            constraints.maxWidth < AppSizes.profileContentMaxWidth;

        return SingleChildScrollView(
          padding: EdgeInsets.all(isCompact ? AppSpacing.md : AppSpacing.lg),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(
                maxWidth: AppSizes.profileContentMaxWidth,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  ProfileIdentityCard(
                    name: _displayName,
                    roleLabel: RoleFormatter.label(session.role),
                    phoneNumber: _displayPhone,
                    isCompact: isCompact,
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ProfileSection(
                    title: AppStrings.PROFILE_ACCOUNT_DETAILS,
                    subtitle: AppStrings.PROFILE_ACCOUNT_DETAILS_HINT,
                    child: _DetailGrid(
                      fields: [
                        ProfileDetailField(
                          icon: Icons.badge_outlined,
                          label: AppStrings.PROFILE_FIELD_NAME,
                          value: _displayName,
                        ),
                        ProfileDetailField(
                          icon: Icons.call_outlined,
                          label: AppStrings.PROFILE_FIELD_PHONE,
                          value: _displayPhone,
                        ),
                        ProfileDetailField(
                          icon: Icons.workspace_premium_outlined,
                          label: AppStrings.PROFILE_FIELD_ROLE,
                          value: RoleFormatter.label(session.role),
                        ),
                        ProfileDetailField(
                          icon: Icons.tag_rounded,
                          label: AppStrings.PROFILE_FIELD_USER_ID,
                          value: session.userId > 0
                              ? '${session.userId}'
                              : AppStrings.PROFILE_VALUE_UNKNOWN,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ProfileSection(
                    title: AppStrings.PROFILE_PERMISSIONS,
                    subtitle: AppStrings.PROFILE_PERMISSIONS_HINT,
                    child: _PermissionGrid(
                      rows: [
                        ProfilePermissionRow(
                          label:
                              AppStrings.PROFILE_PERMISSION_CREATE_ADMIN,
                          isGranted: session.canCreateAdmin,
                        ),
                        ProfilePermissionRow(
                          label: AppStrings
                              .PROFILE_PERMISSION_CREATE_SALES_PERSON,
                          isGranted: session.canCreateSalesPerson,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ProfileSection(
                    title: AppStrings.PROFILE_SESSION_SECTION,
                    subtitle: AppStrings.PROFILE_SESSION_HINT,
                    child: const _LogoutRow(),
                  ),
                  const SizedBox(height: AppSpacing.lg),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  String get _displayName => session.name.trim().isEmpty
      ? AppStrings.PROFILE_VALUE_UNKNOWN
      : session.name.trim();

  String get _displayPhone => session.phoneNumber.trim().isEmpty
      ? AppStrings.PROFILE_VALUE_UNKNOWN
      : session.phoneNumber.trim();
}

class _DetailGrid extends StatelessWidget {
  final List<Widget> fields;

  const _DetailGrid({required this.fields});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isTwoColumn =
            constraints.maxWidth >= AppSizes.profileDetailMinWidth * 2;
        final double itemWidth = isTwoColumn
            ? (constraints.maxWidth - AppSpacing.smd) / 2
            : constraints.maxWidth;

        return Wrap(
          spacing: AppSpacing.smd,
          runSpacing: AppSpacing.smd,
          children: fields
              .map((field) => SizedBox(width: itemWidth, child: field))
              .toList(),
        );
      },
    );
  }
}

class _PermissionGrid extends StatelessWidget {
  final List<Widget> rows;

  const _PermissionGrid({required this.rows});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final bool isTwoColumn =
            constraints.maxWidth >= AppSizes.profilePermissionMinWidth * 2;
        final double itemWidth = isTwoColumn
            ? (constraints.maxWidth - AppSpacing.smd) / 2
            : constraints.maxWidth;

        return Wrap(
          spacing: AppSpacing.smd,
          runSpacing: AppSpacing.smd,
          children: rows
              .map((row) => SizedBox(width: itemWidth, child: row))
              .toList(),
        );
      },
    );
  }
}

class _LogoutRow extends StatelessWidget {
  const _LogoutRow();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          child: Text(
            AppStrings.LOGOUT_CONFIRM_BODY,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        SecondaryButton(
          label: AppStrings.LOGOUT,
          icon: Icons.logout_rounded,
          onPressed: () => LogoutAction.run(context),
        ),
      ],
    );
  }
}
