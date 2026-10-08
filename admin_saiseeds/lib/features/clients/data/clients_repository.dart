import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/clients_endpoints.dart';
import '../../../core/network/endpoints/utilities_endpoints.dart';
import '../../orders/data/models/child_org_model.dart';
import 'models/client_model.dart';
import 'models/paginated_clients_model.dart';

class ClientsRepository {
  final ApiClient _apiClient;

  const ClientsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  /// The client's existing "Delivery To" places, for the picker on an order
  /// or custom order -- unscoped on the admin side, unlike the Android
  /// endpoint which is scoped to the caller's own clients.
  Future<List<ChildOrgModel>> fetchClientChildren(String clientPublicId) async {
    final dynamic response = await _apiClient.get(
      UtilitiesEndpoints.clientChildren,
      queryParams: {'client_public_id': clientPublicId},
    );

    if (response is! List) return const [];
    return response
        .whereType<Map>()
        .map((entry) => ChildOrgModel.fromJson(Map<String, dynamic>.from(entry)))
        .toList();
  }

  Future<PaginatedClientsModel> fetchClients({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      ClientsEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedClientsModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<ClientModel> fetchClient(String publicId) async {
    final dynamic response = await _apiClient.get(
      ClientsEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return ClientModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<void> verifyClient(String publicId) async {
    await _apiClient.post(
      ClientsEndpoints.verify,
      body: {'public_id': publicId},
    );
  }

  Future<void> updateClient(ClientModel client) async {
    await _apiClient.post(ClientsEndpoints.update, body: client.toUpdateJson());
  }
}
