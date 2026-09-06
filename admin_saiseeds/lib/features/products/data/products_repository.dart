import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/products_endpoints.dart';
import 'models/product_model.dart';

class ProductsRepository {
  final ApiClient _apiClient;

  const ProductsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<ProductModel>> fetchProducts() async {
    final dynamic response = await _apiClient.get(ProductsEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map((item) => ProductModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<void> createProduct({
    required String name,
    required int cropId,
    required String buyingPrice,
    required String sellingPrice,
  }) async {
    await _apiClient.post(
      ProductsEndpoints.create,
      body: {
        'name': name,
        'crop': cropId,
        'buying_price': buyingPrice,
        'selling_price': sellingPrice,
      },
    );
  }

  Future<void> updateProduct({
    required String publicId,
    required String name,
    required int cropId,
    required String buyingPrice,
    required String sellingPrice,
  }) async {
    await _apiClient.patch(
      ProductsEndpoints.detail(publicId),
      body: {
        'name': name,
        'crop': cropId,
        'buying_price': buyingPrice,
        'selling_price': sellingPrice,
      },
    );
  }

  Future<void> deleteProduct(String publicId) async {
    await _apiClient.delete(ProductsEndpoints.detail(publicId));
  }
}
