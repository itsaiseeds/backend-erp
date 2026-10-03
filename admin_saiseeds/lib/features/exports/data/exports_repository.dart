import '../../../core/constants/app_strings.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/api_exception.dart';
import 'models/export_kind.dart';

class ExportsRepository {
  final ApiClient _apiClient;

  const ExportsRepository({required ApiClient apiClient})
    : _apiClient = apiClient;

  /// Fetches one report.
  ///
  /// The window is required for every export but inventory snapshots, which
  /// returns the full history when it is omitted. That one is paginated, so
  /// `all=true` pulls it in a single call rather than a page walk.
  Future<Map<String, dynamic>> fetchExport({
    required ExportKind kind,
    String? startDate,
    String? endDate,
  }) async {
    final Map<String, dynamic> params = {
      if (startDate != null && startDate.isNotEmpty) 'start_date': startDate,
      if (endDate != null && endDate.isNotEmpty) 'end_date': endDate,
      if (kind.isPaginated) 'all': true,
    };

    final dynamic response = await _apiClient.get(
      kind.endpoint,
      queryParams: params,
    );

    if (response is! Map) {
      throw const ApiException(message: AppStrings.SOMETHING_WENT_WRONG);
    }

    return Map<String, dynamic>.from(response);
  }
}
