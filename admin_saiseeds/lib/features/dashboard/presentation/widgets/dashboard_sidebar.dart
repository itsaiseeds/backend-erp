import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/constants/tab_ids.dart';
import '../../../../core/models/sidebar_item_model.dart';
import '../../../../core/utils/formatters/role_formatter.dart';
import '../../../../core/widgets/layout/app_sidebar.dart';
import '../../../auth/presentation/bloc/session_cubit.dart';
import '../../../auth/presentation/logout_action.dart';

class DashboardSidebar extends StatelessWidget {
  final List<SidebarItemModel> items;
  final String activeItemId;
  final ValueChanged<String> onItemSelected;
  final bool isCollapsed;
  final VoidCallback? onToggleCollapse;

  const DashboardSidebar({
    super.key,
    required this.items,
    required this.activeItemId,
    required this.onItemSelected,
    required this.isCollapsed,
    this.onToggleCollapse,
  });

  @override
  Widget build(BuildContext context) {
    return AppSidebar(
      items: items,
      activeItemId: activeItemId,
      onItemSelected: onItemSelected,
      isCollapsed: isCollapsed,
      onToggleCollapse: onToggleCollapse,
      onLogout: () => LogoutAction.run(context),
      profileCard: BlocBuilder<SessionCubit, SessionState>(
        builder: (context, state) {
          final session = state.session;
          final bool isLoading = state.status == SessionStatus.loading;
          return SidebarProfileCard(
            name: isLoading
                ? null
                : (session?.name.isNotEmpty ?? false
                      ? session!.name
                      : AppStrings.PROFILE_VALUE_UNKNOWN),
            roleLabel: RoleFormatter.label(session?.role),
            isCollapsed: isCollapsed,
            isActive: activeItemId == TabIds.PROFILE,
            onTap: () => onItemSelected(TabIds.PROFILE),
          );
        },
      ),
    );
  }
}
