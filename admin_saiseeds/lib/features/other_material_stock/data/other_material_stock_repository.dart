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
    // Per product packaging rather than one row per material type: the same
    // leaflet is a different stock position for a 1.5 kg bag than a 5 kg one.
    final dynamic response = await _apiClient.get(
      InventoryEndpoints.otherMaterialStock,
      queryParams: const {'group_by': 'configuration'},
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return OtherMaterialStockModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }
}
