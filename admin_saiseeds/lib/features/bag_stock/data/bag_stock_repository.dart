import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/inventory_endpoints.dart';
import 'models/bag_stock_line_model.dart';

class BagStockRepository {
  final ApiClient _apiClient;

  const BagStockRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<BagStockSnapshotModel> fetchBagStock() async {
    final dynamic response = await _apiClient.get(InventoryEndpoints.bagStock);

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return BagStockSnapshotModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> replaceBagStock(Map<String, int> counts) async {
    await _apiClient.post(
      InventoryEndpoints.updateBagStock,
      body: {'counts': counts},
    );
  }

  Future<void> patchBagStock(Map<String, int> counts) async {
    await _apiClient.patch(
      InventoryEndpoints.updateBagStock,
      body: {'counts': counts},
    );
  }
}
