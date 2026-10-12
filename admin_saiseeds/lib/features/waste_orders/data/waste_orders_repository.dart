import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/waste_orders_endpoints.dart';
import '../../custom_orders/data/models/custom_order_model.dart';
import '../../custom_orders/data/models/paginated_custom_orders_model.dart';

/// A waste order is a [CustomOrderModel] with ``made_from_waste`` true, so
/// this reuses the same response models as [CustomOrdersRepository] -- only
/// the endpoints (and the shape of what gets posted to them) are its own.
class WasteOrdersRepository {
  final ApiClient _apiClient;

  const WasteOrdersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedCustomOrdersModel> fetchWasteOrders({
    Map<String, dynamic>? queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      WasteOrdersEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedCustomOrdersModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<CustomOrderModel> fetchWasteOrder(String publicId) async {
    final dynamic response = await _apiClient.get(
      WasteOrdersEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return CustomOrderModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> createWasteOrder(Map<String, dynamic> body) async {
    await _apiClient.post(WasteOrdersEndpoints.create, body: body);
  }

  Future<void> updateWasteOrder({
    required String publicId,
    required Map<String, dynamic> changes,
  }) async {
    await _apiClient.patch(
      WasteOrdersEndpoints.edit(publicId),
      body: changes,
    );
  }

  Future<void> deleteWasteOrder(String publicId) async {
    await _apiClient.delete(WasteOrdersEndpoints.detail(publicId));
  }

  Future<void> dispatchWasteOrder({
    required String publicId,
    required Map<String, dynamic> body,
  }) async {
    await _apiClient.post(WasteOrdersEndpoints.dispatch(publicId), body: body);
  }

  Future<void> revertDispatch(String publicId) async {
    await _apiClient.post(WasteOrdersEndpoints.revertDispatch(publicId));
  }

  Future<void> markDelivered(String publicId) async {
    await _apiClient.post(WasteOrdersEndpoints.markDelivered(publicId));
  }
}
