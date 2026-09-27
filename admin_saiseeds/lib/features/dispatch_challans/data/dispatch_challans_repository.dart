import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/orders_endpoints.dart';
import 'models/paginated_dispatch_challans_model.dart';

class DispatchChallansRepository {
  final ApiClient _apiClient;

  const DispatchChallansRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedDispatchChallansModel> fetchChallans({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      OrdersEndpoints.dispatchChallans,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedDispatchChallansModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

}
