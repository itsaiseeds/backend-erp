import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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

    return AppShell(
      isCollapsed: isCollapsed,
      sidebar: DashboardSidebar(
        items: SidebarItems.ITEMS,
        activeItemId: _activeItemId,
        onItemSelected: _onItemSelected,
        isCollapsed: isCollapsed,
        onToggleCollapse: _onToggleCollapse,
      ),
      content: DashboardContentSwitcher.screenFor(_activeItemId),
    );
  }
}
