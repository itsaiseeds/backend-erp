import 'package:flutter/material.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/tab_ids.dart';
import '../../../core/constants/user_roles.dart';
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
      id: TabIds.PRODUCT_STOCK,
      label: AppStrings.PRODUCT_STOCK,
      icon: Icons.inventory_outlined,
    ),
    SidebarItemModel(
      id: TabIds.RAW_MATERIAL_STOCK,
      label: AppStrings.RAW_MATERIAL_STOCK,
      icon: Icons.grass_outlined,
    ),
  ];

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
