import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';
import '../../auth/presentation/bloc/session_cubit.dart';
import '../../../core/routing/route_constants.dart';
import '../../../core/utils/responsive/responsive_helper.dart';
import '../../../core/widgets/layout/app_shell.dart';
import '../data/sidebar_items.dart';
import 'widgets/dashboard_content_switcher.dart';
import 'widgets/dashboard_sidebar.dart';

class DashboardScreen extends StatefulWidget {
  final String? tab;

  const DashboardScreen({super.key, this.tab});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late String _activeItemId;
  bool _isCollapsedByUser = false;
  bool _hasUserSetCollapse = false;

  @override
  void initState() {
    super.initState();
    _activeItemId = SidebarItems.isKnown(widget.tab)
        ? widget.tab!
        : SidebarItems.DEFAULT_ITEM_ID;

    if (!SidebarItems.isKnown(widget.tab)) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _syncUrl());
    }
  }

  @override
  void didUpdateWidget(DashboardScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.tab == oldWidget.tab) return;

    final String resolved = SidebarItems.isKnown(widget.tab)
        ? widget.tab!
        : SidebarItems.DEFAULT_ITEM_ID;

    if (resolved == _activeItemId) return;
    setState(() => _activeItemId = resolved);

    if (!SidebarItems.isKnown(widget.tab)) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _syncUrl());
    }
  }

  void _syncUrl() {
    if (!mounted) return;
    GoRouter.of(context).goNamed(
      RouteNames.DASHBOARD,
      queryParameters: {RouteQueryParams.TAB: _activeItemId},
    );
  }

  void _onItemSelected(String itemId) {
    if (_activeItemId == itemId) return;
    setState(() => _activeItemId = itemId);
    _syncUrl();
  }

  void _onToggleCollapse() {
    final bool next = !_resolveIsCollapsed();
    setState(() {
      _hasUserSetCollapse = true;
      _isCollapsedByUser = next;
    });
  }

  bool _resolveIsCollapsed() {
    if (_hasUserSetCollapse) return _isCollapsedByUser;
    return !ResponsiveHelper.isDesktop(context);
  }

  @override
  Widget build(BuildContext context) {
    final bool isCollapsed = _resolveIsCollapsed();

    return BlocBuilder<SessionCubit, SessionState>(
      builder: (context, state) {
        final String? role = state.session?.role;
        final bool isResolved = state.status == SessionStatus.loaded;

        final String activeId =
            !isResolved || SidebarItems.isAccessible(_activeItemId, role: role)
            ? _activeItemId
            : SidebarItems.DEFAULT_ITEM_ID;

        if (activeId != _activeItemId) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted) return;
            setState(() => _activeItemId = activeId);
            _syncUrl();
          });
        }

        return AppShell(
          isCollapsed: isCollapsed,
          sidebar: DashboardSidebar(
            items: SidebarItems.visibleItems(role: role),
            activeItemId: activeId,
            onItemSelected: _onItemSelected,
            isCollapsed: isCollapsed,
            onToggleCollapse: _onToggleCollapse,
          ),
          content: DashboardContentSwitcher.screenFor(activeId),
        );
      },
    );
  }
}
