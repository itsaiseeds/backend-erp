import 'package:flutter/material.dart';
import '../../../../core/constants/tab_ids.dart';
import '../../../profile/presentation/profile_screen.dart';
import '../views/admins_view.dart';
import '../views/dashboard_overview_view.dart';
import '../views/sales_people_view.dart';

class DashboardContentSwitcher {
  DashboardContentSwitcher._();

  static Widget screenFor(String tabId) {
    switch (tabId) {
      case TabIds.PROFILE:
        return const ProfileScreen();
      case TabIds.ADMINS:
        return const AdminsView();
      case TabIds.SALES_PEOPLE:
        return const SalesPeopleView();
      case TabIds.DASHBOARD:
      default:
        return const DashboardOverviewView();
    }
  }
}
