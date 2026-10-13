import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import 'models/product_transfer_result_model.dart';

class ProductStockTransferRepository {
  final ApiClient _apiClient;

  const ProductStockTransferRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<ProductTransferResult> transfer({
    required String sourceProductPublicId,
    required String targetProductPublicId,
    required String quantityKg,
  }) async {
    final dynamic response = await _apiClient.post(
      InventoryEndpoints.transferProduct,
      body: {
        'source_product': sourceProductPublicId,
        'target_product': targetProductPublicId,
        'quantity_kg': quantityKg,
      },
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return ProductTransferResult.fromJson(Map<String, dynamic>.from(response));
  }
}
