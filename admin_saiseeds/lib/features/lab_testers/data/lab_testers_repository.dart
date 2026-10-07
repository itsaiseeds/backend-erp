import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/lab_testers_endpoints.dart';
import 'models/lab_tester_model.dart';

class LabTestersRepository {
  final ApiClient _apiClient;

  const LabTestersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<LabTesterModel>> fetchLabTesters() async {
    final dynamic response = await _apiClient.get(LabTestersEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map((item) => LabTesterModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<void> createLabTester({
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    await _apiClient.post(
      LabTestersEndpoints.create,
      body: {'name': name, 'email': email, 'phone_number': phoneNumber},
    );
  }

  Future<void> updateLabTester({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    await _apiClient.patch(
      LabTestersEndpoints.detail(id),
      body: {'name': name, 'email': email, 'phone_number': phoneNumber},
    );
  }

  Future<void> deleteLabTester(String id) async {
    await _apiClient.delete(LabTestersEndpoints.detail(id));
  }
}
