import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/orders_endpoints.dart';
import 'models/dispatch_lot_number_model.dart';

class DispatchLotNumbersRepository {
  final ApiClient _apiClient;

  const DispatchLotNumbersRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<List<DispatchLotNumberModel>> fetchLotNumbers() async {
    final dynamic response = await _apiClient.get(
      OrdersEndpoints.dispatchLotNumbers,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    final Map<String, dynamic> body = Map<String, dynamic>.from(response);
    final dynamic raw = body['results'] ?? body['data'];

    if (raw is! List) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    final List<DispatchLotNumberModel> lots = raw
        .whereType<Map>()
        .map(
          (Map<dynamic, dynamic> entry) =>
              DispatchLotNumberModel.fromJson(Map<String, dynamic>.from(entry)),
        )
        .where((DispatchLotNumberModel lot) => lot.lotNumber.trim().isNotEmpty)
        .toList();

    lots.sort(
      (DispatchLotNumberModel a, DispatchLotNumberModel b) =>
          b.lastUsedAt.compareTo(a.lastUsedAt),
    );

    return lots;
  }
}
