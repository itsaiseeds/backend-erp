import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/return_orders_endpoints.dart';
import 'models/paginated_return_orders_model.dart';
import 'models/return_order_edit_model.dart';
import 'models/return_recipe_model.dart';

class ReturnOrdersRepository {
  final ApiClient _apiClient;

  const ReturnOrdersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedReturnOrdersModel> fetchReturnOrders({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      ReturnOrdersEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedReturnOrdersModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<ReturnOrderRecipesModel> fetchRecipes(String publicId) async {
    final dynamic response = await _apiClient.get(
      ReturnOrdersEndpoints.recipes(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return ReturnOrderRecipesModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  /// Edit is a full replacement of the return's lines, so the body always
  /// carries the whole return.
  Future<void> updateReturn({
    required String publicId,
    required ReturnOrderEditRequest request,
  }) {
    return _apiClient.patch(
      ReturnOrdersEndpoints.edit(publicId),
      body: request.toJson(),
    );
  }

  Future<void> acceptReturn({
    required String publicId,
    required bool includeInOtherRawMaterials,
    required List<String> recipePublicIds,
  }) {
    return _apiClient.post(
      ReturnOrdersEndpoints.accept(publicId),
      body: {
        'include_in_other_raw_materials': includeInOtherRawMaterials,
        'recipe_public_ids': includeInOtherRawMaterials
            ? recipePublicIds
            : const <String>[],
      },
    );
  }

  Future<void> rejectReturn(String publicId) =>
      _apiClient.post(ReturnOrdersEndpoints.reject(publicId));

  Future<void> unrejectReturn(String publicId) =>
      _apiClient.post(ReturnOrdersEndpoints.unreject(publicId));

  Future<void> revertAcceptReturn(String publicId) =>
      _apiClient.post(ReturnOrdersEndpoints.revertAccept(publicId));
}
