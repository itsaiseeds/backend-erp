import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/sales_people_endpoints.dart';
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
}
