import 'package:flutter/material.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/constants/tab_ids.dart';
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
      id: TabIds.PROFILE,
      label: AppStrings.PROFILE,
      icon: Icons.person_outline_rounded,
    ),
  ];

  static const String DEFAULT_ITEM_ID = TabIds.DASHBOARD;

  static bool isKnown(String? id) =>
      id != null && ITEMS.any((item) => item.id == id);
}
