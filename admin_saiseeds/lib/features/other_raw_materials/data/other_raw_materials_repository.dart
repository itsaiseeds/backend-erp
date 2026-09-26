import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/raw_materials_endpoints.dart';
import 'models/other_material_type_model.dart';
import 'models/paginated_other_material_recipes_model.dart';

class OtherRawMaterialsRepository {
  final ApiClient _apiClient;

  const OtherRawMaterialsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedOtherMaterialRecipesModel> fetchRecipes({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      RawMaterialsEndpoints.recipesList,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedOtherMaterialRecipesModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<List<OtherMaterialTypeModel>> fetchMaterialTypes() async {
    final dynamic response = await _apiClient.get(
      RawMaterialsEndpoints.otherMaterialTypes,
    );

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map(
          (item) =>
              OtherMaterialTypeModel.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<void> createRecipe({
    required String productPublicId,
    required int materialTypeId,
    required String packetWeight,
    required String quantity,
  }) async {
    await _apiClient.post(
      RawMaterialsEndpoints.recipesCreate,
      body: _body(
        productPublicId: productPublicId,
        materialTypeId: materialTypeId,
        packetWeight: packetWeight,
        quantity: quantity,
      ),
    );
  }

  Future<void> updateRecipe({
    required String publicId,
    required String productPublicId,
    required int materialTypeId,
    required String packetWeight,
    required String quantity,
  }) async {
    await _apiClient.patch(
      RawMaterialsEndpoints.recipeDetail(publicId),
      body: _body(
        productPublicId: productPublicId,
        materialTypeId: materialTypeId,
        packetWeight: packetWeight,
        quantity: quantity,
      ),
    );
  }

  Future<void> deleteRecipe(String publicId) async {
    await _apiClient.delete(RawMaterialsEndpoints.recipeDetail(publicId));
  }

  static Map<String, dynamic> _body({
    required String productPublicId,
    required int materialTypeId,
    required String packetWeight,
    required String quantity,
  }) {
    return {
      'product': productPublicId,
      'material_type': materialTypeId,
      'packet_weight': packetWeight,
      'quantity': quantity,
    };
  }
}
