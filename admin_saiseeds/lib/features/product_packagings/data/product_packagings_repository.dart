import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/product_packagings_endpoints.dart';
import 'models/product_packaging_model.dart';

class ProductPackagingsRepository {
  final ApiClient _apiClient;

  const ProductPackagingsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<ProductPackagingModel>> fetchProductPackagings() async {
    final dynamic response = await _apiClient.get(
      ProductPackagingsEndpoints.list,
    );

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map(
          (item) =>
              ProductPackagingModel.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<void> createProductPackaging({
    required String productPublicId,
    required String packingBagWeight,
    required String packingBags,
    required String sellingPrice,
  }) async {
    await _apiClient.post(
      ProductPackagingsEndpoints.create,
      body: _body(
        productPublicId: productPublicId,
        packingBagWeight: packingBagWeight,
        packingBags: packingBags,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<void> updateProductPackaging({
    required String publicId,
    required String productPublicId,
    required String packingBagWeight,
    required String packingBags,
    required String sellingPrice,
  }) async {
    await _apiClient.patch(
      ProductPackagingsEndpoints.detail(publicId),
      body: _body(
        productPublicId: productPublicId,
        packingBagWeight: packingBagWeight,
        packingBags: packingBags,
        sellingPrice: sellingPrice,
      ),
    );
  }

  Future<void> deleteProductPackaging(String publicId) async {
    await _apiClient.delete(ProductPackagingsEndpoints.detail(publicId));
  }

  static Map<String, dynamic> _body({
    required String productPublicId,
    required String packingBagWeight,
    required String packingBags,
    required String sellingPrice,
  }) {
    return {
      'product': productPublicId,
      'packing_bag_weight': packingBagWeight,
      'packing_bags': int.tryParse(packingBags.trim()) ?? 0,
      'selling_price': sellingPrice,
    };
  }
}
