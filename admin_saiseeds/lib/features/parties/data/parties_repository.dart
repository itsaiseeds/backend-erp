import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/parties_endpoints.dart';
import 'models/paginated_parties_model.dart';

class PartiesRepository {
  final ApiClient _apiClient;

  const PartiesRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedPartiesModel> fetchParties({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      PartiesEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedPartiesModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> createParty({
    required String name,
    required int cityId,
    String? contactNumber,
  }) async {
    await _apiClient.post(
      PartiesEndpoints.create,
      body: {
        'name': name,
        'city': cityId,
        'contact_number': contactNumber,
      },
    );
  }

  Future<void> updateParty({
    required int id,
    required String name,
    required int cityId,
    String? contactNumber,
  }) async {
    await _apiClient.patch(
      PartiesEndpoints.detail(id),
      body: {
        'name': name,
        'city': cityId,
        'contact_number': contactNumber,
      },
    );
  }

  Future<void> deleteParty(int id) async {
    await _apiClient.delete(PartiesEndpoints.detail(id));
  }
}
