class ReturnOrdersEndpoints {
  ReturnOrdersEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/return-orders/';

  static String recipes(String publicId) =>
      '$_base/return-order-recipes/$publicId';

  static String edit(String publicId) => '$_base/edit-return-order/$publicId';

  static String accept(String publicId) =>
      '$_base/accept-return-order/$publicId';

  static String reject(String publicId) => '$_base/reject-return-order/$publicId';

  static String unreject(String publicId) =>
      '$_base/unreject-return-order/$publicId';

  static String revertAccept(String publicId) =>
      '$_base/revert-accept-return-order/$publicId';
}
