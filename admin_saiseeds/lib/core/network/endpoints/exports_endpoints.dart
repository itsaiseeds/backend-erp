class ExportsEndpoints {
  ExportsEndpoints._();

  static const String _base = '/api/sales-admin/export';

  static const String orders = '$_base/orders';

  static const String customOrders = '$_base/custom-orders';

  static const String dispatchReceipts = '$_base/dispatch-receipts';

  static const String inwardEntries = '$_base/inward-entries';

  static const String inventorySnapshots = '$_base/inventory-snapshots';

  static const String labTestings = '$_base/lab-testings';
}
