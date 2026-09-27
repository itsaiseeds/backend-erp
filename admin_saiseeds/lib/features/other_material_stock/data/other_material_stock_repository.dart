import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import 'models/other_material_stock_model.dart';

class OtherMaterialStockRepository {
  final ApiClient _apiClient;

  const OtherMaterialStockRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<OtherMaterialStockModel> fetchOtherMaterialStock() async {
    final dynamic response = await _apiClient.get(
      InventoryEndpoints.otherMaterialStock,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return OtherMaterialStockModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }
}
