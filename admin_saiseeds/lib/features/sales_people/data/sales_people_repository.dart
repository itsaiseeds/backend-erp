import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/sales_people_endpoints.dart';
import '../../clients/data/models/paginated_clients_model.dart';
import 'models/old_sales_person_model.dart';
import 'models/sales_person_model.dart';

class SalesPeopleRepository {
  final ApiClient _apiClient;

  const SalesPeopleRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<SalesPersonModel>> fetchSalesPeople() async {
    final dynamic response = await _apiClient.get(SalesPeopleEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map(
          (item) => SalesPersonModel.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<void> createSalesPerson({
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    await _apiClient.post(
      SalesPeopleEndpoints.create,
      body: {
        'name': name,
        'email': email,
        'phone_number': phoneNumber,
        'city': cityId,
      },
    );
  }

  Future<void> updateSalesPerson({
    required String id,
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    await _apiClient.patch(
      SalesPeopleEndpoints.detail(id),
      body: {
        'name': name,
        'email': email,
        'phone_number': phoneNumber,
        'city': cityId,
      },
    );
  }

  Future<void> deleteSalesPerson(String id) async {
    await _apiClient.delete(SalesPeopleEndpoints.detail(id));
  }

  /// Every sales person, removed ones included -- the source picker for a
  /// client transfer.
  Future<List<OldSalesPersonModel>> fetchAllSalesPeople() async {
    final dynamic response = await _apiClient.get(
      SalesPeopleEndpoints.allIncludingRemoved,
    );

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map(
          (item) =>
              OldSalesPersonModel.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<PaginatedClientsModel> fetchClientsBySalesPerson({
    required int salesPersonId,
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      SalesPeopleEndpoints.byLiveSalesPerson(salesPersonId),
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedClientsModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<int> transferClients({
    required List<String> clientIds,
    required int targetSalesPersonId,
  }) async {
    final dynamic response = await _apiClient.post(
      SalesPeopleEndpoints.transferClients,
      body: {
        'client_ids': clientIds,
        'target_sales_person_id': targetSalesPersonId,
      },
    );

    if (response is Map && response['transferred_count'] != null) {
      final dynamic count = response['transferred_count'];
      if (count is int) return count;
      if (count is num) return count.toInt();
    }
    return clientIds.length;
  }
}
