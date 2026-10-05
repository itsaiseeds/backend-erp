import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/field_trips_repository.dart';
import '../../data/models/farmer_visit_model.dart';
import '../../data/models/field_trip_model.dart';
import '../../data/models/paginated_field_trips_model.dart';

enum FieldTripsStatus { initial, loading, loaded, failure }

class FieldTripsState extends Equatable {
  final FieldTripsStatus status;
  final List<FieldTripModel> trips;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final bool isMutating;
  final String? errorMessage;

  const FieldTripsState({
    this.status = FieldTripsStatus.initial,
    this.trips = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {
      FieldTripsCubit.STATUS_FILTER: FieldTripStatus.PLANNED_CODE,
    },
    this.isMutating = false,
    this.errorMessage,
  });

  bool get isEmptySource => (search?.trim().isEmpty ?? true) && filters.isEmpty;

  bool get hasMore => currentPage < totalPages;

  FieldTripsState copyWith({
    FieldTripsStatus? status,
    List<FieldTripModel>? trips,
    List<ClientFilterModel>? availableFilters,
    List<ClientSortModel>? availableSorts,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return FieldTripsState(
      status: status ?? this.status,
      trips: trips ?? this.trips,
      availableFilters: availableFilters ?? this.availableFilters,
      availableSorts: availableSorts ?? this.availableSorts,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      search: search ?? this.search,
      sortBy: sortBy ?? this.sortBy,
      sortOrder: sortOrder ?? this.sortOrder,
      filters: filters ?? this.filters,
      isMutating: isMutating ?? this.isMutating,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
    status,
    trips,
    availableFilters,
    availableSorts,
    currentPage,
    totalPages,
    totalItems,
    search,
    sortBy,
    sortOrder,
    filters,
    isMutating,
    errorMessage,
  ];
}

class FieldTripsCubit extends SafeCubit<FieldTripsState> {
  final FieldTripsRepository _repository;

  FieldTripsCubit({required FieldTripsRepository repository})
    : _repository = repository,
      super(const FieldTripsState());

  static const int PAGE_SIZE = 10;
  static const String STATUS_FILTER = 'status';

  Future<void> loadTrips() => _fetch(page: state.currentPage);

  Future<void> refresh() => _fetch(page: 1);

  Future<void> applyQuery({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) async {
    emit(
      state.copyWith(
        currentPage: page,
        search: search ?? '',
        sortBy: sortBy ?? '',
        sortOrder: sortOrder ?? '',
        filters: filters ?? const {},
      ),
    );
    await _fetch(page: page);
  }

  Future<List<FarmerVisitModel>> loadFarmerVisits(String publicId) =>
      _repository.fetchFarmerVisits(publicId);

  Future<bool> updateTrip({
    required String publicId,
    int? cityId,
    String? village,
    String? expectedStartAt,
    String? expectedEndAt,
  }) {
    return _mutate(
      () => _repository.updateFieldTrip(
        publicId: publicId,
        cityId: cityId,
        village: village,
        expectedStartAt: expectedStartAt,
        expectedEndAt: expectedEndAt,
      ),
    );
  }

  Future<bool> approveTrip(String publicId) =>
      _mutate(() => _repository.approveFieldTrip(publicId));

  Future<bool> unapproveTrip(String publicId) =>
      _mutate(() => _repository.unapproveFieldTrip(publicId));

  Future<bool> deleteTrip(String publicId) =>
      _mutate(() => _repository.deleteFieldTrip(publicId));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await _fetch(page: state.currentPage);
      return true;
    } on ApiException catch (e) {
      emit(state.copyWith(isMutating: false, errorMessage: e.message));
      return false;
    } catch (_) {
      emit(
        state.copyWith(
          isMutating: false,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
      return false;
    }
  }

  ClientFilterModel? _filterFor(String key) {
    for (final ClientFilterModel filter in state.availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {'page': page, 'page_size': PAGE_SIZE};

    final String search = state.search?.trim() ?? '';
    if (search.isNotEmpty) params['village'] = search;

    state.filters.forEach((key, value) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;

      // A range arrives as one "from|to" value but the API wants it as two
      // bound params, named by the filter itself.
      final ClientFilterModel? filter = _filterFor(key);
      if (filter != null && filter.kind == ClientFilterKind.datetimeRange) {
        final List<String> bounds = trimmed.split(DateRangeValue.SEPARATOR);
        final String lower = bounds.isNotEmpty ? bounds.first.trim() : '';
        final String upper = bounds.length > 1 ? bounds[1].trim() : '';
        if (lower.isNotEmpty) params[filter.lowerBoundParam] = lower;
        if (upper.isNotEmpty) params[filter.upperBoundParam] = upper;
        return;
      }

      params[key] = trimmed;
    });

    final String sort = state.sortBy?.trim() ?? '';
    if (sort.isNotEmpty) {
      final bool isDescending =
          (state.sortOrder ?? '') == AppFilterSearchBar.SORT_DESCENDING;
      params['sort'] = isDescending ? '-$sort' : sort;
    }

    return params;
  }

  /// Pulls the next page and appends it, for scroll-to-load.
  Future<void> loadMore() async {
    if (!state.hasMore) return;
    if (state.status == FieldTripsStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
  }

  Future<void> _fetch({required int page, bool append = false}) async {
    emit(state.copyWith(status: FieldTripsStatus.loading, clearError: true));

    try {
      final PaginatedFieldTripsModel result = await _repository.fetchFieldTrips(
        queryParams: _buildQueryParams(page),
      );

      emit(
        state.copyWith(
          status: FieldTripsStatus.loaded,
          trips: append ? [...state.trips, ...result.results] : result.results,
          availableFilters: result.availableFilters.isEmpty
              ? state.availableFilters
              : result.availableFilters,
          availableSorts: result.availableSorts.isEmpty
              ? state.availableSorts
              : result.availableSorts,
          currentPage: page,
          totalPages: result.totalPages,
          totalItems: result.totalCount,
        ),
      );
    } on ApiException catch (e) {
      emit(
        state.copyWith(
          status: FieldTripsStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: FieldTripsStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
