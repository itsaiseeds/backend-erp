import 'package:dio/dio.dart';
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
    required int stageId,
    required String sellingPrice,
    ProductImageUpload? image,
    List<String> descriptionItems = const [],
  }) async {
    await _apiClient.post(
      ProductsEndpoints.create,
      body: _body(
        name: name,
        cropId: cropId,
        stageId: stageId,
        sellingPrice: sellingPrice,
        image: image,
        descriptionItems: descriptionItems,
      ),
    );
  }

  Future<void> updateProduct({
    required String publicId,
    required String name,
    required int cropId,
    required int stageId,
    required String sellingPrice,
    ProductImageUpload? image,
    List<String> descriptionItems = const [],
  }) async {
    await _apiClient.patch(
      ProductsEndpoints.detail(publicId),
      body: _body(
        name: name,
        cropId: cropId,
        stageId: stageId,
        sellingPrice: sellingPrice,
        image: image,
        descriptionItems: descriptionItems,
      ),
    );
  }

  static dynamic _body({
    required String name,
    required int cropId,
    required int stageId,
    required String sellingPrice,
    required ProductImageUpload? image,
    required List<String> descriptionItems,
  }) {
    final List<String> items = descriptionItems
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList();

    if (image == null) {
      return {
        'name': name,
        'crop': cropId,
        'stage': stageId,
        'selling_price': sellingPrice,
        'description_items': items,
      };
    }

    // An ImageField needs multipart; the list repeats its key, which is how
    // DRF reads a many-valued field out of form data.
    return FormData.fromMap({
      'name': name,
      'crop': '$cropId',
      'stage': '$stageId',
      'selling_price': sellingPrice,
      'description_items': items,
      'image': MultipartFile.fromBytes(image.bytes, filename: image.filename),
    });
  }

  Future<void> deleteProduct(String publicId) async {
    await _apiClient.delete(ProductsEndpoints.detail(publicId));
  }
}
