import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../../clients/data/models/client_model.dart';
import '../../../clients/data/models/paginated_clients_model.dart';
import '../../../sales_people/data/models/old_sales_person_model.dart';
import '../../../sales_people/data/sales_people_repository.dart';

enum TransferClientStatus { initial, loading, loaded, failure }

class TransferClientState extends Equatable {
  final TransferClientStatus status;
  final OldSalesPersonModel? sourceSalesPerson;
  final List<OldSalesPersonModel> sourceOptions;
  final List<ClientModel> clients;
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
  final String? transferErrorMessage;

  const TransferClientState({
    this.status = TransferClientStatus.initial,
    this.sourceSalesPerson,
    this.sourceOptions = const [],
    this.clients = const [],
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
    this.transferErrorMessage,
  });

  bool get hasSource => sourceSalesPerson != null;

  TransferClientState copyWith({
    TransferClientStatus? status,
    OldSalesPersonModel? sourceSalesPerson,
    bool clearSource = false,
    List<OldSalesPersonModel>? sourceOptions,
    List<ClientModel>? clients,
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
    String? transferErrorMessage,
    bool clearTransferError = false,
  }) {
    return TransferClientState(
      status: status ?? this.status,
      sourceSalesPerson: clearSource
          ? null
          : (sourceSalesPerson ?? this.sourceSalesPerson),
      sourceOptions: sourceOptions ?? this.sourceOptions,
      clients: clients ?? this.clients,
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
      transferErrorMessage: clearTransferError
          ? null
          : (transferErrorMessage ?? this.transferErrorMessage),
    );
  }

  bool get hasMore => currentPage < totalPages;

  @override
  List<Object?> get props => [
    status,
    sourceSalesPerson,
    sourceOptions,
    clients,
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
    transferErrorMessage,
  ];
}

class TransferClientCubit extends SafeCubit<TransferClientState> {
  final SalesPeopleRepository _repository;

  TransferClientCubit({required SalesPeopleRepository repository})
    : _repository = repository,
      super(const TransferClientState());

  static const int PAGE_SIZE = 10;
  static const String COMPANY_NAME_FILTER = 'company_name';

  Future<void> loadSourceOptions() async {
    try {
      final List<OldSalesPersonModel> all = await _repository
          .fetchAllSalesPeople();
      emit(state.copyWith(sourceOptions: all));
    } catch (_) {
      // The picker simply stays empty; the table keeps its own error path.
    }
  }

  Future<void> selectSource(OldSalesPersonModel? person) async {
    if (person == null) {
      emit(
        const TransferClientState().copyWith(
          sourceOptions: state.sourceOptions,
        ),
      );
      return;
    }

    emit(
      state.copyWith(
        sourceSalesPerson: person,
        currentPage: 1,
        search: '',
        sortBy: '',
        sortOrder: '',
        filters: const {},
      ),
    );
    await _fetch(page: 1);
  }

  Future<void> applyQuery({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) async {
    if (!state.hasSource) return;

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

  Future<void> refresh() {
    if (!state.hasSource) return Future.value();
    return _fetch(page: 1);
  }

  Future<void> loadMore() async {
    if (!state.hasSource) return;
    if (!state.hasMore) return;
    if (state.status == TransferClientStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
  }

  Future<bool> transferClients({
    required List<String> clientIds,
    required int targetSalesPersonId,
  }) async {
    emit(state.copyWith(isMutating: true, clearTransferError: true));

    try {
      await _repository.transferClients(
        clientIds: clientIds,
        targetSalesPersonId: targetSalesPersonId,
      );
      emit(state.copyWith(isMutating: false));
      await refresh();
      return true;
    } on ApiException catch (e) {
      emit(
        state.copyWith(isMutating: false, transferErrorMessage: e.message),
      );
      return false;
    } catch (_) {
      emit(
        state.copyWith(
          isMutating: false,
          transferErrorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
      return false;
    }
  }

  ClientFilterModel? _filterFor(String key) {
    for (final filter in state.availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {'page': page, 'page_size': PAGE_SIZE};

    state.filters.forEach((key, value) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;

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

    final String query = state.search?.trim() ?? '';
    if (query.isNotEmpty && !params.containsKey(COMPANY_NAME_FILTER)) {
      params[COMPANY_NAME_FILTER] = query;
    }

    final String sort = state.sortBy?.trim() ?? '';
    if (sort.isNotEmpty) {
      final bool isDescending =
          (state.sortOrder ?? '') == AppFilterSearchBar.SORT_DESCENDING;
      params['sort'] = isDescending ? '-$sort' : sort;
    }

    return params;
  }

  Future<void> _fetch({required int page, bool append = false}) async {
    final OldSalesPersonModel? source = state.sourceSalesPerson;
    if (source == null) return;

    emit(state.copyWith(status: TransferClientStatus.loading, clearError: true));

    try {
      final PaginatedClientsModel result = await _repository
          .fetchClientsBySalesPerson(
            salesPersonId: source.id,
            queryParams: _buildQueryParams(page),
          );

      emit(
        state.copyWith(
          status: TransferClientStatus.loaded,
          clients: append ? [...state.clients, ...result.results] : result.results,
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
          status: TransferClientStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: TransferClientStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
