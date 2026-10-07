import 'package:flutter/material.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/tab_ids.dart';
import '../../../core/constants/user_roles.dart';
import '../../../core/models/sidebar_workspace_model.dart';
import '../../../core/models/sidebar_item_model.dart';

class SidebarItems {
  SidebarItems._();

  static const List<SidebarItemModel> ITEMS = [
    SidebarItemModel(
      id: TabIds.DASHBOARD,
      label: AppStrings.DASHBOARD,
      icon: Icons.space_dashboard_outlined,
    ),
    SidebarItemModel(
      id: TabIds.ADMINS,
      label: AppStrings.ADMINS,
      icon: Icons.admin_panel_settings_outlined,
    ),
    SidebarItemModel(
      id: TabIds.SALES_PEOPLE,
      label: AppStrings.SALES_PEOPLE,
      icon: Icons.groups_outlined,
    ),
    SidebarItemModel(
      id: TabIds.GODOWN_MANAGERS,
      label: AppStrings.GODOWN_MANAGERS,
      icon: Icons.warehouse_outlined,
    ),
    SidebarItemModel(
      id: TabIds.CLIENTS,
      label: AppStrings.CLIENTS,
      icon: Icons.storefront_outlined,
    ),
    SidebarItemModel(
      id: TabIds.ORDERS,
      label: AppStrings.ORDERS,
      icon: Icons.receipt_long_outlined,
    ),
    SidebarItemModel(
      id: TabIds.RETURN_ORDERS,
      label: AppStrings.RETURN_ORDERS,
      icon: Icons.assignment_return_outlined,
    ),
    SidebarItemModel(
      id: TabIds.DISPATCH_CHALLANS,
      label: AppStrings.DISPATCH_CHALLANS,
      icon: Icons.local_shipping_outlined,
    ),
    SidebarItemModel(
      id: TabIds.CUSTOM_ORDERS,
      label: AppStrings.CUSTOM_ORDERS,
      icon: Icons.tune_outlined,
    ),
    SidebarItemModel(
      id: TabIds.EXPORTS,
      label: AppStrings.EXPORTS,
      icon: Icons.download_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PRODUCTS,
      label: AppStrings.PRODUCTS,
      icon: Icons.inventory_2_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PRODUCT_PACKAGINGS,
      label: AppStrings.PRODUCT_PACKAGINGS,
      icon: Icons.inventory_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PARTIES,
      label: AppStrings.PARTIES,
      icon: Icons.handshake_outlined,
    ),
    SidebarItemModel(
      id: TabIds.BAG_STOCK,
      label: AppStrings.BAG_STOCK,
      icon: Icons.warehouse_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PACKET_STOCK,
      label: AppStrings.PACKET_STOCK,
      icon: Icons.category_outlined,
    ),
    SidebarItemModel(
      id: TabIds.INWARD_RAW_MATERIALS,
      label: AppStrings.INWARD_RAW_MATERIALS,
      icon: Icons.local_shipping_outlined,
    ),
    SidebarItemModel(
      id: TabIds.OTHER_RAW_MATERIALS,
      label: AppStrings.OTHER_RAW_MATERIALS,
      icon: Icons.layers_outlined,
    ),
    SidebarItemModel(
      id: TabIds.OTHER_MATERIAL_INWARD,
      label: AppStrings.OTHER_MATERIAL_INWARD,
      icon: Icons.inventory_2_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PURCHASE_TRACKING,
      label: AppStrings.PURCHASE_TRACKING,
      icon: Icons.shopping_bag_outlined,
    ),
    SidebarItemModel(
      id: TabIds.WASTE_MANAGEMENT,
      label: AppStrings.WASTE_MANAGEMENT,
      icon: Icons.delete_sweep_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PRODUCT_STOCK,
      label: AppStrings.PRODUCT_STOCK,
      icon: Icons.inventory_outlined,
    ),
    SidebarItemModel(
      id: TabIds.RAW_MATERIAL_STOCK,
      label: AppStrings.RAW_MATERIAL_STOCK,
      icon: Icons.grass_outlined,
    ),
    SidebarItemModel(
      id: TabIds.OTHER_MATERIAL_STOCK,
      label: AppStrings.OTHER_MATERIAL_STOCK,
      icon: Icons.layers_outlined,
    ),
    SidebarItemModel(
      id: TabIds.FIELD_TRIPS,
      label: AppStrings.FIELD_TRIPS,
      icon: Icons.map_outlined,
    ),
    SidebarItemModel(
      id: TabIds.FARMERS,
      label: AppStrings.FARMERS,
      icon: Icons.agriculture_outlined,
    ),
  ];

  static const SidebarWorkspaceModel OPERATIONS = SidebarWorkspaceModel(
    id: 'operations',
    label: AppStrings.WORKSPACE_OPERATIONS,
    hint: AppStrings.WORKSPACE_OPERATIONS_HINT,
    icon: Icons.bolt_outlined,
    groups: [
      SidebarGroupModel(id: 'ops-home', itemIds: [TabIds.DASHBOARD]),
      SidebarGroupModel(
        id: 'ops-orders',
        label: AppStrings.GROUP_ORDERS,
        itemIds: [
          TabIds.ORDERS,
          TabIds.RETURN_ORDERS,
          TabIds.CUSTOM_ORDERS,
          TabIds.DISPATCH_CHALLANS,
        ],
      ),
      SidebarGroupModel(
        id: 'ops-daily-stock',
        label: AppStrings.GROUP_DAILY_STOCK,
        itemIds: [TabIds.BAG_STOCK, TabIds.PACKET_STOCK],
      ),
      SidebarGroupModel(
        id: 'ops-stock-analysis',
        label: AppStrings.GROUP_STOCK_ANALYSIS,
        itemIds: [
          TabIds.PRODUCT_STOCK,
          TabIds.RAW_MATERIAL_STOCK,
          TabIds.OTHER_MATERIAL_STOCK,
        ],
      ),
      SidebarGroupModel(
        id: 'ops-inward',
        label: AppStrings.GROUP_INWARD,
        itemIds: [
          TabIds.INWARD_RAW_MATERIALS,
          TabIds.OTHER_MATERIAL_INWARD,
          TabIds.PURCHASE_TRACKING,
        ],
      ),
      SidebarGroupModel(
        id: 'ops-waste',
        label: AppStrings.GROUP_WASTE_MANAGEMENT,
        itemIds: [TabIds.WASTE_MANAGEMENT],
      ),
      SidebarGroupModel(id: 'ops-exports', itemIds: [TabIds.EXPORTS]),
    ],
  );

  static const SidebarWorkspaceModel SETUP = SidebarWorkspaceModel(
    id: 'setup',
    label: AppStrings.WORKSPACE_SETUP,
    hint: AppStrings.WORKSPACE_SETUP_HINT,
    icon: Icons.tune_outlined,
    groups: [
      SidebarGroupModel(
        id: 'setup-catalogue',
        label: AppStrings.GROUP_CATALOGUE,
        itemIds: [
          TabIds.PRODUCTS,
          TabIds.PRODUCT_PACKAGINGS,
          TabIds.OTHER_RAW_MATERIALS,
        ],
      ),
      SidebarGroupModel(
        id: 'setup-onboarding',
        label: AppStrings.GROUP_ONBOARDING,
        itemIds: [TabIds.CLIENTS, TabIds.PARTIES],
      ),
      SidebarGroupModel(
        id: 'setup-farmer-trips',
        label: AppStrings.GROUP_FARMER_TRIPS,
        itemIds: [TabIds.FIELD_TRIPS, TabIds.FARMERS],
      ),
      SidebarGroupModel(
        id: 'setup-users',
        label: AppStrings.GROUP_USER_MANAGEMENT,
        itemIds: [TabIds.SALES_PEOPLE, TabIds.GODOWN_MANAGERS, TabIds.ADMINS],
      ),
    ],
  );

  static const List<SidebarWorkspaceModel> WORKSPACES = [OPERATIONS, SETUP];

  static const String DEFAULT_WORKSPACE_ID = 'operations';

  /// Resolves both workspaces against the role, dropping any group - or
  /// whole workspace - the role cannot see a single tab in.
  static List<ResolvedSidebarWorkspace> visibleWorkspaces({
    required String? role,
  }) {
    final List<SidebarItemModel> permitted = visibleItems(role: role);
    if (permitted.isEmpty) return const [];

    final Map<String, SidebarItemModel> byId = {
      for (final SidebarItemModel item in permitted) item.id: item,
    };

    final List<ResolvedSidebarWorkspace> resolved = [];

    for (final SidebarWorkspaceModel workspace in WORKSPACES) {
      final List<ResolvedSidebarGroup> groups = [];

      for (final SidebarGroupModel group in workspace.groups) {
        final List<SidebarItemModel> items = [
          for (final String id in group.itemIds)
            if (byId.containsKey(id)) byId[id]!,
        ];
        if (items.isEmpty) continue;
        groups.add(ResolvedSidebarGroup(group: group, items: items));
      }

      if (groups.isEmpty) continue;
      resolved.add(
        ResolvedSidebarWorkspace(workspace: workspace, groups: groups),
      );
    }

    return resolved;
  }

  /// The workspace that owns [itemId], so selecting a tab by URL opens the
  /// side of the app it lives in.
  static String workspaceIdFor(String? itemId) {
    if (itemId == null) return DEFAULT_WORKSPACE_ID;
    for (final SidebarWorkspaceModel workspace in WORKSPACES) {
      if (workspace.itemIds.contains(itemId)) return workspace.id;
    }
    return DEFAULT_WORKSPACE_ID;
  }

  static const String DEFAULT_ITEM_ID = TabIds.DASHBOARD;

  static const List<String> _NON_NAV_TAB_IDS = [TabIds.PROFILE];

  static List<SidebarItemModel> visibleItems({required String? role}) {
    return ITEMS.where((item) => _isPermitted(item.id, role: role)).toList();
  }

  static bool _isPermitted(String id, {required String? role}) {
    if (!UserRoles.canAccessPortal(role)) return false;
    if (id == TabIds.ADMINS) return UserRoles.isSuperuser(role);
    return true;
  }

  static bool isAccessible(String? id, {required String? role}) {
    if (!isKnown(id)) return false;
    return _isPermitted(id!, role: role);
  }

  static bool isKnown(String? id) =>
      id != null &&
      (ITEMS.any((item) => item.id == id) || _NON_NAV_TAB_IDS.contains(id));
}
