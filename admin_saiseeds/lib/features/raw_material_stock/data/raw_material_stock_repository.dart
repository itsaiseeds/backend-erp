import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import 'models/raw_material_stock_model.dart';

class RawMaterialStockRepository {
  final ApiClient _apiClient;

  const RawMaterialStockRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<RawMaterialStockModel> fetchRawMaterialStock() async {
    final dynamic response = await _apiClient.get(
      InventoryEndpoints.rawMaterialStock,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return RawMaterialStockModel.fromJson(Map<String, dynamic>.from(response));
  }
}
