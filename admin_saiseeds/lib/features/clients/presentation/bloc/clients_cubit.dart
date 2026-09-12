import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../data/clients_repository.dart';
import '../../data/models/client_filter_model.dart';
import '../../data/models/client_model.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../data/models/client_status.dart';
import '../../data/models/paginated_clients_model.dart';

enum ClientsStatus { initial, loading, loaded, failure }

enum ClientsViewMode { pending, verified }

class ClientsState extends Equatable {
  final ClientsStatus status;
  final ClientsViewMode view;
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

  const ClientsState({
    this.status = ClientsStatus.initial,
    this.view = ClientsViewMode.verified,
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
  });

  ClientsState copyWith({
    ClientsStatus? status,
    ClientsViewMode? view,
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
  }) {
    return ClientsState(
      status: status ?? this.status,
      view: view ?? this.view,
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
    );
  }

  bool get isEmptySource => status == ClientsStatus.loaded && clients.isEmpty;

  ClientFilterModel? filterFor(String key) {
    for (final filter in availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  @override
  List<Object?> get props => [
    status,
    view,
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
  ];
}

class ClientsCubit extends SafeCubit<ClientsState> {
  final ClientsRepository _repository;

  ClientsCubit({required ClientsRepository repository})
    : _repository = repository,
      super(const ClientsState());

  static const String STATUS_FILTER = 'status';
  static const String COMPANY_NAME_FILTER = 'company_name';
  static const String ADDRESS_FILTER = 'address';
  static const int PAGE_SIZE = 10;

  Future<void> loadClients() => _fetch(page: state.currentPage);

  Future<void> refresh() => _fetch(page: 1);

  Future<void> selectView(ClientsViewMode view) async {
    if (view == state.view) return;
    emit(state.copyWith(view: view, currentPage: 1));
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

  Future<bool> verifyClient(String publicId) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await _repository.verifyClient(publicId);
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

  Future<bool> updateClient(ClientModel client) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await _repository.updateClient(client);
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

  Future<ClientModel?> fetchClient(String publicId) async {
    try {
      return await _repository.fetchClient(publicId);
    } catch (_) {
      return null;
    }
  }

  ClientFilterModel? _filterFor(String key) {
    for (final filter in state.availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {
      'page': page,
      'page_size': PAGE_SIZE,
      STATUS_FILTER: state.view == ClientsViewMode.pending
          ? ClientStatusX.VERIFICATION_PENDING
          : ClientStatusX.VERIFIED,
    };

    state.filters.forEach((key, value) {
      if (key == STATUS_FILTER) return;

      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;

      final ClientFilterModel? filter = _filterFor(key);
      if (filter != null && filter.kind == ClientFilterKind.datetimeRange) {
        final List<String> bounds = trimmed.split(
          DateRangeValue.SEPARATOR,
        );
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

  Future<void> _fetch({required int page}) async {
    emit(state.copyWith(status: ClientsStatus.loading, clearError: true));

    try {
      final PaginatedClientsModel result = await _repository.fetchClients(
        queryParams: _buildQueryParams(page),
      );

      emit(
        state.copyWith(
          status: ClientsStatus.loaded,
          clients: result.results,
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
        state.copyWith(status: ClientsStatus.failure, errorMessage: e.message),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: ClientsStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
