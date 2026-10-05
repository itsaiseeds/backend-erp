import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/godown_managers_endpoints.dart';
import 'models/godown_manager_model.dart';

class GodownManagersRepository {
  final ApiClient _apiClient;

  const GodownManagersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<GodownManagerModel>> fetchGodownManagers() async {
    final dynamic response = await _apiClient.get(GodownManagersEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map(
          (item) =>
              GodownManagerModel.fromJson(Map<String, dynamic>.from(item)),
        )
        .toList();
  }

  Future<void> createGodownManager({
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    await _apiClient.post(
      GodownManagersEndpoints.create,
      body: {'name': name, 'email': email, 'phone_number': phoneNumber},
    );
  }

  Future<void> updateGodownManager({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    await _apiClient.patch(
      GodownManagersEndpoints.detail(id),
      body: {'name': name, 'email': email, 'phone_number': phoneNumber},
    );
  }

  Future<void> deleteGodownManager(String id) async {
    await _apiClient.delete(GodownManagersEndpoints.detail(id));
  }
}
