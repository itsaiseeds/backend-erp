import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import '../../../core/network/endpoints/lab_testing_report_endpoints.dart';
import 'models/lab_testing_report_model.dart';
import 'models/paginated_lab_testing_report_model.dart';

/// Read-only: lab tests are entered and edited from the lab tester's own
/// app, never from here (see `android.api.v1.LabTestingsView`).
class LabTestingReportRepository {
  final ApiClient _apiClient;

  const LabTestingReportRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  Future<PaginatedLabTestingReportModel> fetchTests({
    required Map<String, dynamic> queryParams,
  }) async {
    final dynamic response = await _apiClient.get(
      LabTestingReportEndpoints.list,
      queryParams: queryParams,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return PaginatedLabTestingReportModel.fromJson(
      Map<String, dynamic>.from(response),
    );
  }

  Future<LabTestingReportModel> fetchTest(String publicId) async {
    final dynamic response = await _apiClient.get(
      LabTestingReportEndpoints.detail(publicId),
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return LabTestingReportModel.fromJson(Map<String, dynamic>.from(response));
  }
}
