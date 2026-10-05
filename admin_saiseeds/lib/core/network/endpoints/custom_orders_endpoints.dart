class CustomOrdersEndpoints {
  CustomOrdersEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/custom-orders/';

  static const String create = '$_base/create-custom-order';

  static String detail(String publicId) => '$_base/custom-order/$publicId';

  static String edit(String publicId) => '$_base/edit-custom-order/$publicId';

  static String dispatch(String publicId) =>
      '$_base/dispatch-custom-order/$publicId';

  static String revertDispatch(String publicId) =>
      '$_base/revert-custom-order-dispatch/$publicId';
}
