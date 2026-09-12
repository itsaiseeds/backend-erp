import 'client_filter_model.dart';
import 'client_model.dart';

class PaginatedClientsModel {
  final int totalCount;
  final int totalPages;
  final int? nextPageNumber;
  final int? previousPageNumber;
  final List<ClientModel> results;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;

  const PaginatedClientsModel({
    this.totalCount = 0,
    this.totalPages = 0,
    this.nextPageNumber,
    this.previousPageNumber,
    this.results = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
  });

  factory PaginatedClientsModel.fromJson(Map<String, dynamic> json) {
    return PaginatedClientsModel(
      totalCount: _asInt(json['total_count']),
      totalPages: _asInt(json['total_pages']),
      nextPageNumber: _asNullableInt(json['next_page_number']),
      previousPageNumber: _asNullableInt(json['previous_page_number']),
      results: _listOf(json['results'], ClientModel.fromJson),
      availableFilters: _listOf(
        json['available_filters'],
        ClientFilterModel.fromJson,
      ),
      availableSorts: _listOf(
        json['available_sorts'],
        ClientSortModel.fromJson,
      ),
    );
  }

  static List<T> _listOf<T>(
    dynamic value,
    T Function(Map<String, dynamic>) parser,
  ) {
    if (value is! List) return const [];
    return value
        .whereType<Map>()
        .map((entry) => parser(Map<String, dynamic>.from(entry)))
        .toList();
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  static int? _asNullableInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is num) return value.toInt();
    if (value is String) return int.tryParse(value);
    return null;
  }
}
