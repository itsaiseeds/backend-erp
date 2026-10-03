import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/endpoints/exports_endpoints.dart';

/// One downloadable report.
///
/// Every export shares the same shape -- a date window in, a list of rows
/// out -- so the kind carries what differs: where to fetch it, what to call
/// the file, and how to flatten its rows into a sheet.
enum ExportKind {
  orders,
  customOrders,
  dispatchReceipts,
  inwardEntries,
  inventorySnapshots,
}

extension ExportKindX on ExportKind {
  String get endpoint {
    switch (this) {
      case ExportKind.orders:
        return ExportsEndpoints.orders;
      case ExportKind.customOrders:
        return ExportsEndpoints.customOrders;
      case ExportKind.dispatchReceipts:
        return ExportsEndpoints.dispatchReceipts;
      case ExportKind.inwardEntries:
        return ExportsEndpoints.inwardEntries;
      case ExportKind.inventorySnapshots:
        return ExportsEndpoints.inventorySnapshots;
    }
  }

  String get label {
    switch (this) {
      case ExportKind.orders:
        return AppStrings.EXPORT_ORDERS;
      case ExportKind.customOrders:
        return AppStrings.EXPORT_CUSTOM_ORDERS;
      case ExportKind.dispatchReceipts:
        return AppStrings.EXPORT_DISPATCH_RECEIPTS;
      case ExportKind.inwardEntries:
        return AppStrings.EXPORT_INWARD_ENTRIES;
      case ExportKind.inventorySnapshots:
        return AppStrings.EXPORT_INVENTORY_SNAPSHOTS;
    }
  }

  String get description {
    switch (this) {
      case ExportKind.orders:
        return AppStrings.EXPORT_ORDERS_BODY;
      case ExportKind.customOrders:
        return AppStrings.EXPORT_CUSTOM_ORDERS_BODY;
      case ExportKind.dispatchReceipts:
        return AppStrings.EXPORT_DISPATCH_RECEIPTS_BODY;
      case ExportKind.inwardEntries:
        return AppStrings.EXPORT_INWARD_ENTRIES_BODY;
      case ExportKind.inventorySnapshots:
        return AppStrings.EXPORT_INVENTORY_SNAPSHOTS_BODY;
    }
  }

  IconData get icon {
    switch (this) {
      case ExportKind.orders:
        return Icons.receipt_long_outlined;
      case ExportKind.customOrders:
        return Icons.tune_outlined;
      case ExportKind.dispatchReceipts:
        return Icons.local_shipping_outlined;
      case ExportKind.inwardEntries:
        return Icons.input_outlined;
      case ExportKind.inventorySnapshots:
        return Icons.inventory_outlined;
    }
  }

  /// Stem of the saved file; the date window and extension are appended.
  String get fileStem {
    switch (this) {
      case ExportKind.orders:
        return 'orders';
      case ExportKind.customOrders:
        return 'custom-orders';
      case ExportKind.dispatchReceipts:
        return 'dispatch-receipts';
      case ExportKind.inwardEntries:
        return 'inward-entries';
      case ExportKind.inventorySnapshots:
        return 'inventory-snapshots';
    }
  }

  /// Inventory snapshots page rather than taking a required window, so the
  /// dates are optional there and `all=true` fetches the lot in one call.
  bool get isPaginated => this == ExportKind.inventorySnapshots;

  /// Only dispatch receipts have a printable document behind each row, so
  /// only they can be downloaded as challan PDFs instead of a sheet.
  bool get supportsReceipts => this == ExportKind.dispatchReceipts;
}
