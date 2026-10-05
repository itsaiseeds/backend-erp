import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/custom_orders_endpoints.dart';
import 'models/custom_order_model.dart';
import 'models/paginated_custom_orders_model.dart';

class CustomOrdersRepository {
  final ApiClient _apiClient;

  const CustomOrdersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedCustomOrdersModel> fetchCustomOrders({
    Map<String, dynamic>? queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      CustomOrdersEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedCustomOrdersModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<CustomOrderModel> fetchCustomOrder(String publicId) async {
    final dynamic response = await _apiClient.get(
      CustomOrdersEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return CustomOrderModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> createCustomOrder(Map<String, dynamic> body) async {
    await _apiClient.post(CustomOrdersEndpoints.create, body: body);
  }

  Future<void> updateCustomOrder({
    required String publicId,
    required Map<String, dynamic> changes,
  }) async {
    await _apiClient.patch(CustomOrdersEndpoints.edit(publicId), body: changes);
  }

  Future<void> deleteCustomOrder(String publicId) async {
    await _apiClient.delete(CustomOrdersEndpoints.detail(publicId));
  }

  Future<void> dispatchCustomOrder({
    required String publicId,
    required Map<String, dynamic> body,
  }) async {
    await _apiClient.post(CustomOrdersEndpoints.dispatch(publicId), body: body);
  }

  Future<void> revertDispatch(String publicId) async {
    await _apiClient.post(CustomOrdersEndpoints.revertDispatch(publicId));
  }
}
