class PurchaseTrackingEndpoints {
  PurchaseTrackingEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/non-stock-inwards';
  static const String create = '$_base/non-stock-inwards';

  static String detail(String publicId) => '$_base/non-stock-inward/$publicId';
}
