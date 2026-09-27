import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/raw_materials_endpoints.dart';
import 'models/paginated_other_material_inward_model.dart';

class OtherMaterialInwardRepository {
  final ApiClient _apiClient;

  const OtherMaterialInwardRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedOtherMaterialInwardModel> fetchLots({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      RawMaterialsEndpoints.otherInwardList,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedOtherMaterialInwardModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<void> createLot({
    required int partyId,
    required String recipePublicId,
    required String quantity,
  }) async {
    await _apiClient.post(
      RawMaterialsEndpoints.otherInwardCreate,
      body: {
        'party': partyId,
        'recipe': recipePublicId,
        'quantity': quantity,
      },
    );
  }

  Future<void> deleteLot(String publicId) async {
    await _apiClient.delete(RawMaterialsEndpoints.otherInwardDetail(publicId));
  }
}
