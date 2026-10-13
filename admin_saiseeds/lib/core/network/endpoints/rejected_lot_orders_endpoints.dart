class RejectedLotOrdersEndpoints {
  RejectedLotOrdersEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/rejected-orders/';

  static const String create = '$_base/create-rejected-order';

  static String detail(String publicId) => '$_base/rejected-order/$publicId';

  static String farmers(int partyId) => '$_base/rejected-orders/$partyId';

  static String lots(int partyId, String farmerName) =>
      '$_base/rejected-orders/$partyId/${Uri.encodeComponent(farmerName)}';
}
