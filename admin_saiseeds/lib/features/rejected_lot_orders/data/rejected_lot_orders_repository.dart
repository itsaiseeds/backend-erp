import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/rejected_lot_orders_endpoints.dart';
import '../../custom_orders/data/models/custom_order_model.dart';
import '../../custom_orders/data/models/paginated_custom_orders_model.dart';
import 'models/rejected_farmer_model.dart';
import 'models/rejected_lot_model.dart';

class RejectedLotOrdersRepository {
  final ApiClient _apiClient;

  const RejectedLotOrdersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedCustomOrdersModel> fetchRejectedOrders({
    Map<String, dynamic>? queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      RejectedLotOrdersEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedCustomOrdersModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<CustomOrderModel> fetchRejectedOrder(String publicId) async {
    final dynamic response = await _apiClient.get(
      RejectedLotOrdersEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return CustomOrderModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<List<RejectedFarmerModel>> fetchFarmers(int partyId) async {
    final dynamic response = await _apiClient.get(
      RejectedLotOrdersEndpoints.farmers(partyId),
    );

    if (response is! List) return const [];
    return response
        .whereType<Map>()
        .map((item) => RejectedFarmerModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<List<RejectedLotModel>> fetchLots(int partyId, String farmerName) async {
    final dynamic response = await _apiClient.get(
      RejectedLotOrdersEndpoints.lots(partyId, farmerName),
    );

    if (response is! List) return const [];
    return response
        .whereType<Map>()
        .map((item) => RejectedLotModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<void> createRejectedOrder(Map<String, dynamic> body) async {
    await _apiClient.post(RejectedLotOrdersEndpoints.create, body: body);
  }

  Future<void> deleteRejectedOrder(String publicId) async {
    await _apiClient.delete(RejectedLotOrdersEndpoints.detail(publicId));
  }
}
