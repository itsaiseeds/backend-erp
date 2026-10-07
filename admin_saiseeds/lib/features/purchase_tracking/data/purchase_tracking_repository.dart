import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/purchase_tracking_endpoints.dart';
import 'models/paginated_purchase_tracking_model.dart';

class PurchaseTrackingRepository {
  final ApiClient _apiClient;

  const PurchaseTrackingRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedPurchaseTrackingModel> fetchEntries({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      PurchaseTrackingEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedPurchaseTrackingModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<void> createEntry({
    required String name,
    required String description,
    required String companyName,
    required String price,
    required String quantity,
    required String unit,
  }) async {
    await _apiClient.post(
      PurchaseTrackingEndpoints.create,
      body: {
        'name': name.trim(),
        'description': description.trim(),
        'company_name': companyName.trim(),
        'price': price.trim().isEmpty ? null : price.trim(),
        'quantity': quantity.trim(),
        'unit': unit,
      },
    );
  }

  Future<void> updateEntry({
    required String publicId,
    required String name,
    required String description,
    required String companyName,
    required String price,
    required String quantity,
    required String unit,
  }) async {
    await _apiClient.patch(
      PurchaseTrackingEndpoints.detail(publicId),
      body: {
        'name': name.trim(),
        'description': description.trim(),
        'company_name': companyName.trim(),
        'price': price.trim().isEmpty ? null : price.trim(),
        'quantity': quantity.trim(),
        'unit': unit,
      },
    );
  }

  Future<void> deleteEntry(String publicId) async {
    await _apiClient.delete(PurchaseTrackingEndpoints.detail(publicId));
  }
}
