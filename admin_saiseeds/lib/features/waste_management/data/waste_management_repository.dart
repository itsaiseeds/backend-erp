import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/waste_management_endpoints.dart';
import 'models/paginated_wastes_model.dart';

class WasteManagementRepository {
  final ApiClient _apiClient;

  const WasteManagementRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedWastesModel> fetchWastes({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      WasteManagementEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedWastesModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> recordWaste({
    required String productPublicId,
    required String quantityKg,
    required String reason,
  }) async {
    await _apiClient.post(
      WasteManagementEndpoints.create,
      body: {
        'product': productPublicId,
        'quantity_kg': quantityKg.trim(),
        'reason': reason.trim(),
      },
    );
  }

  Future<void> updateWaste({
    required String publicId,
    required String quantityKg,
    required String reason,
  }) async {
    await _apiClient.patch(
      WasteManagementEndpoints.detail(publicId),
      body: {'quantity_kg': quantityKg.trim(), 'reason': reason.trim()},
    );
  }

  Future<void> deleteWaste(String publicId) async {
    await _apiClient.delete(WasteManagementEndpoints.detail(publicId));
  }
}
