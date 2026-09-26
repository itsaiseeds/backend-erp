import 'package:flutter/material.dart';
import '../../../../core/constants/tab_ids.dart';
import '../../../profile/presentation/profile_screen.dart';
import '../../../admins/presentation/views/admins_view.dart';
import '../views/dashboard_overview_view.dart';
import '../../../products/presentation/views/products_view.dart';
import '../../../product_packagings/presentation/views/product_packagings_view.dart';
import '../../../clients/presentation/views/clients_view.dart';
import '../../../orders/presentation/views/orders_view.dart';
import '../../../parties/presentation/views/parties_view.dart';
import '../../../bag_stock/presentation/views/bag_stock_view.dart';
import '../../../packet_stock/presentation/views/packet_stock_view.dart';
import '../../../inward_raw_materials/presentation/views/inward_raw_materials_view.dart';
import '../../../other_raw_materials/presentation/views/other_raw_materials_view.dart';
import '../../../other_material_inward/presentation/views/other_material_inward_view.dart';
import '../../../sales_people/presentation/views/sales_people_view.dart';

class DashboardContentSwitcher {
  DashboardContentSwitcher._();

  static Widget screenFor(String tabId) {
    switch (tabId) {
      case TabIds.PROFILE:
        return const ProfileScreen();
      case TabIds.ADMINS:
        return const AdminsView();
      case TabIds.CLIENTS:
        return const ClientsView();
      case TabIds.ORDERS:
        return const OrdersView();
      case TabIds.SALES_PEOPLE:
        return const SalesPeopleView();
      case TabIds.PRODUCTS:
        return const ProductsView();
      case TabIds.PRODUCT_PACKAGINGS:
        return const ProductPackagingsView();
      case TabIds.PARTIES:
        return const PartiesView();
      case TabIds.BAG_STOCK:
        return const BagStockView();
      case TabIds.PACKET_STOCK:
        return const PacketStockView();
      case TabIds.INWARD_RAW_MATERIALS:
        return const InwardRawMaterialsView();
      case TabIds.OTHER_RAW_MATERIALS:
        return const OtherRawMaterialsView();
      case TabIds.OTHER_MATERIAL_INWARD:
        return const OtherMaterialInwardView();
      case TabIds.DASHBOARD:
      default:
        return const DashboardOverviewView();
    }
  }
}
