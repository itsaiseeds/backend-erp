class OrdersEndpoints {
  OrdersEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/orders/';

  static String detail(String publicId) => '$_base/order/$publicId';

  static String edit(String publicId) => '$_base/edit-order/$publicId';

  static String verify(String publicId) => '$_base/verify-order/$publicId';

  static String unverify(String publicId) => '$_base/unverify-order/$publicId';

  static String hold(String publicId) => '$_base/hold-order/$publicId';

  static String reject(String publicId) => '$_base/reject-order/$publicId';
}
