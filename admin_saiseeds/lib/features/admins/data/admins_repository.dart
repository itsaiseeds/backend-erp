import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/admins_endpoints.dart';
import '../../../core/constants/app_strings.dart';
import 'models/admin_model.dart';

class AdminsRepository {
  final ApiClient _apiClient;

  const AdminsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<AdminModel>> fetchAdmins() async {
    final dynamic response = await _apiClient.get(AdminsEndpoints.list);

    if (response is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return response
        .whereType<Map>()
        .map((item) => AdminModel.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  Future<void> createAdmin({
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    await _apiClient.post(
      AdminsEndpoints.create,
      body: {
        'name': name,
        'email': email,
        'phone_number': phoneNumber,
        'city': cityId,
      },
    );
  }

  Future<void> updateAdmin({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    await _apiClient.patch(
      AdminsEndpoints.detail(id),
      body: {'name': name, 'email': email, 'phone_number': phoneNumber},
    );
  }

  Future<void> deleteAdmin(String id) async {
    await _apiClient.delete(AdminsEndpoints.detail(id));
  }
}
