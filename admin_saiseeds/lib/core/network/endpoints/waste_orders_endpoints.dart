import 'custom_orders_endpoints.dart';

/// A waste order is a [CustomOrder] made from the waste pool
/// (``made_from_waste``), so it shares the detail-read, delete and
/// revert-dispatch endpoints with a regular custom order -- only listing,
/// creating, editing and dispatching have their own waste-specific routes.
class WasteOrdersEndpoints {
  WasteOrdersEndpoints._();

  static const String _base = '/api/sales-admin';

  static const String list = '$_base/waste-orders/';

  static const String create = '$_base/create-waste-order';

  static String detail(String publicId) =>
      CustomOrdersEndpoints.detail(publicId);

  static String edit(String publicId) => '$_base/edit-waste-order/$publicId';

  static String dispatch(String publicId) =>
      '$_base/dispatch-waste-order/$publicId';

  static String revertDispatch(String publicId) =>
      CustomOrdersEndpoints.revertDispatch(publicId);
}
