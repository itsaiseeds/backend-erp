import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/dispatch_challans_repository.dart';
import '../../data/models/dispatch_challan_model.dart';
import '../../data/models/paginated_dispatch_challans_model.dart';

enum DispatchChallansStatus { initial, loading, loaded, failure }

class DispatchChallansState extends Equatable {
  final DispatchChallansStatus status;
  final List<DispatchChallanModel> challans;
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

  const DispatchChallansState({
    this.status = DispatchChallansStatus.initial,
    this.challans = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.isMutating = false,
    this.errorMessage,
  });

  bool get isEmptySource => (search?.trim().isEmpty ?? true);

  DispatchChallansState copyWith({
    DispatchChallansStatus? status,
    List<DispatchChallanModel>? challans,
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
    return DispatchChallansState(
      status: status ?? this.status,
      challans: challans ?? this.challans,
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
    challans,
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

class DispatchChallansCubit extends SafeCubit<DispatchChallansState> {
  final DispatchChallansRepository _repository;

  DispatchChallansCubit({required DispatchChallansRepository repository})
    : _repository = repository,
      super(
        DispatchChallansState(filters: {DATE_FILTER: defaultWindow.wireValue}),
      );

  static const int PAGE_SIZE = 10;
  static const String DATE_FILTER = AppStrings.FILTER_BY_DATE_RANGE;
  static const String CITY_FILTER = 'city_id';
  static const String CLIENT_FILTER = 'client';

  /// The endpoint requires a window, so the tab opens on yesterday → today.
  static DateRangeValue get defaultWindow {
    final DateTime now = DateTime.now();
    final DateTime today = DateTime(now.year, now.month, now.day);
    return DateRangeValue(
      start: today.subtract(const Duration(days: 1)),
      end: today,
    );
  }

  Future<void> loadChallans() => _fetch(page: state.currentPage);

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

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {'page': page, 'page_size': PAGE_SIZE};

    state.filters.forEach((key, value) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;
      if (key == DATE_FILTER) return;
      params[key] = trimmed;
    });

    // start/end are mandatory: fall back to the default window rather than
    // let the request 400 when the chip is cleared.
    final DateRangeValue window = DateRangeValue.parse(
      state.filters[DATE_FILTER] ?? '',
    );
    final DateRangeValue effective = window.isEmpty ? defaultWindow : window;

    params['start_date_time'] = _startOf(effective);
    params['end_date_time'] = _endOf(effective);

    final String sort = state.sortBy?.trim() ?? '';
    if (sort.isNotEmpty) {
      final bool isDescending =
          (state.sortOrder ?? '') == AppFilterSearchBar.SORT_DESCENDING;
      params['sort'] = isDescending ? '-$sort' : sort;
    }

    return params;
  }

  static String _startOf(DateRangeValue window) {
    final DateTime start = window.start ?? defaultWindow.start!;
    return DateTime(start.year, start.month, start.day).toIso8601String();
  }

  static String _endOf(DateRangeValue window) {
    final DateTime end = window.end ?? window.start ?? defaultWindow.end!;
    return DateTime(end.year, end.month, end.day, 23, 59, 59).toIso8601String();
  }

  Future<void> _fetch({required int page}) async {
    emit(
      state.copyWith(status: DispatchChallansStatus.loading, clearError: true),
    );

    try {
      final PaginatedDispatchChallansModel result = await _repository
          .fetchChallans(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: DispatchChallansStatus.loaded,
          challans: result.results,
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
          status: DispatchChallansStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: DispatchChallansStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
