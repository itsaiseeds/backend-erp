import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/raw_materials_endpoints.dart';
import 'models/paginated_inward_raw_materials_model.dart';

class InwardRawMaterialsRepository {
  final ApiClient _apiClient;

  const InwardRawMaterialsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedInwardRawMaterialsModel> fetchInwardRawMaterials({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      RawMaterialsEndpoints.inwardList,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedInwardRawMaterialsModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<void> createInwardRawMaterial({
    required String productPublicId,
    required int partyId,
    required String quantityKg,
    required String labSamplingDate,
  }) async {
    await _apiClient.post(
      RawMaterialsEndpoints.inwardCreate,
      body: {
        'product': productPublicId,
        'party': partyId,
        'quantity_kg': quantityKg,
        'lab_sampling_date': labSamplingDate,
      },
    );
  }

  Future<void> updateInwardRawMaterial({
    required String publicId,
    String? labSamplingDate,
    String? status,
  }) async {
    final Map<String, dynamic> body = {};
    if (labSamplingDate != null) body['lab_sampling_date'] = labSamplingDate;
    if (status != null) body['status'] = status;

    await _apiClient.patch(
      RawMaterialsEndpoints.inwardDetail(publicId),
      body: body,
    );
  }

  Future<void> deleteInwardRawMaterial(String publicId) async {
    await _apiClient.delete(RawMaterialsEndpoints.inwardDetail(publicId));
  }
}
