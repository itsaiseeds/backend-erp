import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/paginated_purchase_tracking_model.dart';
import '../../data/models/purchase_tracking_model.dart';
import '../../data/purchase_tracking_repository.dart';

enum PurchaseTrackingStatus { initial, loading, loaded, failure }

class PurchaseTrackingState extends Equatable {
  final PurchaseTrackingStatus status;
  final List<PurchaseTrackingModel> entries;
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

  const PurchaseTrackingState({
    this.status = PurchaseTrackingStatus.initial,
    this.entries = const [],
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

  bool get hasSearch => (search ?? '').trim().isNotEmpty;

  List<PurchaseTrackingModel> get visibleEntries => hasSearch
      ? entries.where((entry) => entry.matchesSearch(search!)).toList()
      : entries;

  bool get isEmptySource => !hasSearch && filters.isEmpty;

  bool get hasMore => currentPage < totalPages;

  PurchaseTrackingState copyWith({
    PurchaseTrackingStatus? status,
    List<PurchaseTrackingModel>? entries,
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
    return PurchaseTrackingState(
      status: status ?? this.status,
      entries: entries ?? this.entries,
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
    entries,
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

class PurchaseTrackingCubit extends SafeCubit<PurchaseTrackingState> {
  final PurchaseTrackingRepository _repository;

  PurchaseTrackingCubit({required PurchaseTrackingRepository repository})
    : _repository = repository,
      super(const PurchaseTrackingState());

  static const int PAGE_SIZE = 10;

  Future<void> loadEntries() => _fetch(page: state.currentPage);

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

  Future<bool> createEntry({
    required String name,
    required String description,
    required String companyName,
    required String price,
    required String quantity,
    required String unit,
  }) {
    return _mutate(
      () => _repository.createEntry(
        name: name,
        description: description,
        companyName: companyName,
        price: price,
        quantity: quantity,
        unit: unit,
      ),
    );
  }

  Future<bool> updateEntry({
    required String publicId,
    required String name,
    required String description,
    required String companyName,
    required String price,
    required String quantity,
    required String unit,
  }) {
    return _mutate(
      () => _repository.updateEntry(
        publicId: publicId,
        name: name,
        description: description,
        companyName: companyName,
        price: price,
        quantity: quantity,
        unit: unit,
      ),
    );
  }

  Future<bool> deleteEntry(String publicId) =>
      _mutate(() => _repository.deleteEntry(publicId));

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

  /// Pulls the next page and appends it, for scroll-to-load.
  Future<void> loadMore() async {
    if (!state.hasMore) return;
    if (state.status == PurchaseTrackingStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
  }

  Future<void> _fetch({required int page, bool append = false}) async {
    emit(
      state.copyWith(
        status: PurchaseTrackingStatus.loading,
        clearError: true,
      ),
    );

    try {
      final PaginatedPurchaseTrackingModel result = await _repository
          .fetchEntries(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: PurchaseTrackingStatus.loaded,
          entries: append
              ? [...state.entries, ...result.results]
              : result.results,
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
          status: PurchaseTrackingStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: PurchaseTrackingStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
