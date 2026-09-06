import '../../../core/constants/app_strings.dart';
import '../../../core/models/crop_model.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/crops_endpoints.dart';

class CropsRepository {
  final ApiClient _apiClient;

  const CropsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<CropModel>> fetchCrops() async {
    final dynamic response = await _apiClient.get(CropsEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map((item) => CropModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<CropModel> createCrop(String name) async {
    final dynamic response = await _apiClient.post(
      CropsEndpoints.create,
      body: {'name': name},
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return CropModel.fromJson(Map<String, dynamic>.from(response));
  }
}
