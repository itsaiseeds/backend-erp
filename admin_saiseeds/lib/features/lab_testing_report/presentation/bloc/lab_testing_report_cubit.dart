import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/lab_testing_report_repository.dart';
import '../../data/models/lab_testing_report_model.dart';
import '../../data/models/paginated_lab_testing_report_model.dart';

enum LabTestingReportStatus { initial, loading, loaded, failure }

class LabTestingReportState extends Equatable {
  final LabTestingReportStatus status;
  final List<LabTestingReportModel> tests;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final String? errorMessage;

  const LabTestingReportState({
    this.status = LabTestingReportStatus.initial,
    this.tests = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.errorMessage,
  });

  bool get hasSearch => (search ?? '').trim().isNotEmpty;

  List<LabTestingReportModel> get visibleTests => hasSearch
      ? tests.where((test) => test.matchesSearch(search!)).toList()
      : tests;

  bool get isEmptySource => !hasSearch && filters.isEmpty;

  bool get hasMore => currentPage < totalPages;

  LabTestingReportState copyWith({
    LabTestingReportStatus? status,
    List<LabTestingReportModel>? tests,
    List<ClientFilterModel>? availableFilters,
    List<ClientSortModel>? availableSorts,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
    String? errorMessage,
    bool clearError = false,
  }) {
    return LabTestingReportState(
      status: status ?? this.status,
      tests: tests ?? this.tests,
      availableFilters: availableFilters ?? this.availableFilters,
      availableSorts: availableSorts ?? this.availableSorts,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      search: search ?? this.search,
      sortBy: sortBy ?? this.sortBy,
      sortOrder: sortOrder ?? this.sortOrder,
      filters: filters ?? this.filters,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
    status,
    tests,
    availableFilters,
    availableSorts,
    currentPage,
    totalPages,
    totalItems,
    search,
    sortBy,
    sortOrder,
    filters,
    errorMessage,
  ];
}

class LabTestingReportCubit extends SafeCubit<LabTestingReportState> {
  final LabTestingReportRepository _repository;

  LabTestingReportCubit({required LabTestingReportRepository repository})
    : _repository = repository,
      super(const LabTestingReportState());

  static const int PAGE_SIZE = 10;

  Future<void> loadTests() => _fetch(page: state.currentPage);

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

  /// Pulls the next page and appends it, for scroll-to-load.
  Future<void> loadMore() async {
    if (!state.hasMore) return;
    if (state.status == LabTestingReportStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
  }

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {'page': page, 'page_size': PAGE_SIZE};

    state.filters.forEach((key, value) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;
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

  Future<void> _fetch({required int page, bool append = false}) async {
    emit(
      state.copyWith(status: LabTestingReportStatus.loading, clearError: true),
    );

    try {
      final PaginatedLabTestingReportModel result = await _repository
          .fetchTests(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: LabTestingReportStatus.loaded,
          tests: append ? [...state.tests, ...result.results] : result.results,
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
          status: LabTestingReportStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: LabTestingReportStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
