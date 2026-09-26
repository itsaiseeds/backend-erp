class InventoryEndpoints {
  InventoryEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String checkTodaysInventory = '$_base/check-todays-inventory';

  static const String bagStock = '$_base/bag-stock';
  static const String updateBagStock = '$_base/update-bag-stock';

  static const String samplePacketStock = '$_base/sample-packet-stock';
  static const String updateSamplePacketStock =
      '$_base/update-sample-packet-stock';

  static String getStock(String publicId) => '$_base/get-stock/$publicId';

  static const String rawMaterialStock = '$_base/raw-material-stock';
}
