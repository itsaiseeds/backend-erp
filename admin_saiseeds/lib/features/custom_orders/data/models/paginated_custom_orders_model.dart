import '../../../clients/data/models/client_filter_model.dart';
import 'custom_order_model.dart';

class PaginatedCustomOrdersModel {
  final int totalCount;
  final int totalPages;
  final int? nextPageNumber;
  final int? previousPageNumber;
  final List<CustomOrderModel> results;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;

  const PaginatedCustomOrdersModel({
    this.totalCount = 0,
    this.totalPages = 0,
    this.nextPageNumber,
    this.previousPageNumber,
    this.results = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
  });

  factory PaginatedCustomOrdersModel.fromJson(Map<String, dynamic> json) {
    final dynamic results = json['results'];
    final dynamic filters = json['available_filters'];
    final dynamic sorts = json['available_sorts'];

    return PaginatedCustomOrdersModel(
      totalCount: _asInt(json['total_count']),
      totalPages: _asInt(json['total_pages']),
      nextPageNumber: _asIntOrNull(json['next_page_number']),
      previousPageNumber: _asIntOrNull(json['previous_page_number']),
      results: results is List
          ? results
                .whereType<Map>()
                .map(
                  (item) => CustomOrderModel.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList()
          : const [],
      availableFilters: filters is List
          ? filters
                .whereType<Map>()
                .map(
                  (item) => ClientFilterModel.fromJson(
                    Map<String, dynamic>.from(item),
                  ),
                )
                .toList()
          : const [],
      availableSorts: sorts is List
          ? sorts
                .whereType<Map>()
                .map(
                  (item) =>
                      ClientSortModel.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList()
          : const [],
    );
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? 0;
  }

  static int? _asIntOrNull(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value');
  }
}
