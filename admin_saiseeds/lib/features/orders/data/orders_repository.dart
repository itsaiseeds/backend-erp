import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/orders_endpoints.dart';
import 'models/order_model.dart';
import 'models/paginated_orders_model.dart';

class OrdersRepository {
  final ApiClient _apiClient;

  const OrdersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedOrdersModel> fetchOrders({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      OrdersEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedOrdersModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<OrderModel> fetchOrder(String publicId) async {
    final dynamic response = await _apiClient.get(
      OrdersEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return OrderModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> verifyOrder(String publicId) =>
      _apiClient.post(OrdersEndpoints.verify(publicId));

  Future<void> unverifyOrder(String publicId) =>
      _apiClient.post(OrdersEndpoints.unverify(publicId));

  Future<void> holdOrder(String publicId) =>
      _apiClient.post(OrdersEndpoints.hold(publicId));

  Future<void> rejectOrder(String publicId) =>
      _apiClient.post(OrdersEndpoints.reject(publicId));

  Future<void> updateOrder({
    required String publicId,
    required Map<String, dynamic> changes,
  }) async {
    await _apiClient.patch(OrdersEndpoints.edit(publicId), body: changes);
  }
}
