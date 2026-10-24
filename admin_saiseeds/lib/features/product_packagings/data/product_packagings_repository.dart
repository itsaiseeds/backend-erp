import 'package:dio/dio.dart';
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
    required String packetWeight,
    required String packets,
    required String sellingPrice,
    ProductPackagingImageUpload? image,
  }) async {
    await _apiClient.post(
      ProductPackagingsEndpoints.create,
      body: _createBody(
        productPublicId: productPublicId,
        packetWeight: packetWeight,
        packets: packets,
        sellingPrice: sellingPrice,
        image: image,
      ),
    );
  }

  /// Only the price and image of an existing packaging can change: its
  /// product, packet weight and packet count are fixed once created, since
  /// orders, challans and stock counts all read them live.
  ///
  /// [image] replaces the packaging's own image; [removeImage] clears it
  /// back to falling through to the product's. The server 400s if both are
  /// set, so callers must only ever pass one.
  Future<void> updateProductPackaging({
    required String publicId,
    required String sellingPrice,
    ProductPackagingImageUpload? image,
    bool removeImage = false,
  }) async {
    assert(
      !(image != null && removeImage),
      'Pass an image to replace, or removeImage to clear -- never both.',
    );

    await _apiClient.patch(
      ProductPackagingsEndpoints.detail(publicId),
      body: _updateBody(
        sellingPrice: sellingPrice,
        image: image,
        removeImage: removeImage,
      ),
    );
  }

  Future<void> deleteProductPackaging(String publicId) async {
    await _apiClient.delete(ProductPackagingsEndpoints.detail(publicId));
  }

  static dynamic _createBody({
    required String productPublicId,
    required String packetWeight,
    required String packets,
    required String sellingPrice,
    required ProductPackagingImageUpload? image,
  }) {
    if (image == null) {
      return {
        'product': productPublicId,
        'packet_weight': packetWeight,
        'packets': int.tryParse(packets.trim()) ?? 0,
        'selling_price': sellingPrice,
      };
    }

    return FormData.fromMap({
      'product': productPublicId,
      'packet_weight': packetWeight,
      'packets': packets.trim(),
      'selling_price': sellingPrice,
      'image': MultipartFile.fromBytes(image.bytes, filename: image.filename),
    });
  }

  static dynamic _updateBody({
    required String sellingPrice,
    required ProductPackagingImageUpload? image,
    required bool removeImage,
  }) {
    if (image == null && !removeImage) {
      return {'selling_price': sellingPrice};
    }

    if (removeImage) {
      return {'selling_price': sellingPrice, 'remove_image': true};
    }

    return FormData.fromMap({
      'selling_price': sellingPrice,
      'image': MultipartFile.fromBytes(image!.bytes, filename: image.filename),
    });
  }
}
