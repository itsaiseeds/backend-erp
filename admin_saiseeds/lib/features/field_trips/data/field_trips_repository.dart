import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/field_trips_endpoints.dart';
import 'models/farmer_visit_model.dart';
import 'models/field_trip_model.dart';
import 'models/paginated_farmers_model.dart';
import 'models/paginated_field_trips_model.dart';

class FieldTripsRepository {
  final ApiClient _apiClient;

  const FieldTripsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedFieldTripsModel> fetchFieldTrips({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      FieldTripsEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedFieldTripsModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  static const int _notFound = 404;

  Future<PaginatedFarmersModel> fetchFarmers({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient
        .get(FieldTripsEndpoints.farmers, queryParams: queryParams)
        .catchError((Object error) {
          // The endpoint is specified but not yet deployed. A bare 404 reads as
          // "this farmer is missing", which is the wrong thing to tell someone
          // looking at an empty tab.
          if (error is ApiException && error.statusCode == _notFound) {
            throw const ApiException(
              message: AppStrings.FARMERS_ENDPOINT_MISSING,
              statusCode: _notFound,
            );
          }
          throw error;
        });

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedFarmersModel.fromJson(Map<String, dynamic>.from(response));
  }

  Future<FieldTripModel> fetchFieldTrip(String publicId) async {
    final dynamic response = await _apiClient.get(
      FieldTripsEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return FieldTripModel.fromJson(Map<String, dynamic>.from(response));
  }

  /// Every farmer recorded on one trip, which is a short list by nature.
  Future<List<FarmerVisitModel>> fetchFarmerVisits(String publicId) async {
    final dynamic response = await _apiClient.get(
      FieldTripsEndpoints.farmerVisits(publicId),
      queryParams: const {'all': true},
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    final dynamic results = response['results'];
    if (results is! List) return const [];

    return results
        .whereType<Map>()
        .map(
          (entry) =>
              FarmerVisitModel.fromJson(Map<String, dynamic>.from(entry)),
        )
        .toList();
  }

  Future<void> updateFieldTrip({
    required String publicId,
    int? cityId,
    String? village,
    String? expectedStartAt,
    String? expectedEndAt,
  }) async {
    final Map<String, dynamic> body = {};
    if (cityId != null) body['city_id'] = cityId;
    if (village != null) body['village'] = village;
    if (expectedStartAt != null) body['expected_start_at'] = expectedStartAt;
    if (expectedEndAt != null) body['expected_end_at'] = expectedEndAt;

    await _apiClient.patch(FieldTripsEndpoints.edit(publicId), body: body);
  }

  Future<void> approveFieldTrip(String publicId) async {
    await _apiClient.post(FieldTripsEndpoints.approve(publicId));
  }

  Future<void> unapproveFieldTrip(String publicId) async {
    await _apiClient.post(FieldTripsEndpoints.unapprove(publicId));
  }

  Future<void> deleteFieldTrip(String publicId) async {
    await _apiClient.delete(FieldTripsEndpoints.detail(publicId));
  }
}
