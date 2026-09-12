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
      id: TabIds.PRODUCTS,
      label: AppStrings.PRODUCTS,
      icon: Icons.inventory_2_outlined,
    ),
    SidebarItemModel(
      id: TabIds.PRODUCT_PACKAGINGS,
      label: AppStrings.PRODUCT_PACKAGINGS,
      icon: Icons.inventory_outlined,
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
