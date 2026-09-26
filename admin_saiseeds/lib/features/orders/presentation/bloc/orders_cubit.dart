import 'dart:async';

import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/order_model.dart';
import '../../data/models/paginated_orders_model.dart';
import '../../data/orders_repository.dart';

enum OrdersStatus { initial, loading, loaded, failure }

class OrdersState extends Equatable {
  final OrdersStatus status;
  final List<OrderModel> orders;
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
  final bool isTodaysStockComplete;

  const OrdersState({
    this.status = OrdersStatus.initial,
    this.orders = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.isTodaysStockComplete = false,
    this.isMutating = false,
    this.errorMessage,
  });

  OrdersState copyWith({
    OrdersStatus? status,
    List<OrderModel>? orders,
    List<ClientFilterModel>? availableFilters,
    List<ClientSortModel>? availableSorts,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
    bool? isTodaysStockComplete,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return OrdersState(
      status: status ?? this.status,
      orders: orders ?? this.orders,
      availableFilters: availableFilters ?? this.availableFilters,
      availableSorts: availableSorts ?? this.availableSorts,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      search: search ?? this.search,
      sortBy: sortBy ?? this.sortBy,
      sortOrder: sortOrder ?? this.sortOrder,
      filters: filters ?? this.filters,
      isTodaysStockComplete:
          isTodaysStockComplete ?? this.isTodaysStockComplete,
      isMutating: isMutating ?? this.isMutating,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  bool get isEmptySource => status == OrdersStatus.loaded && orders.isEmpty;

  @override
  List<Object?> get props => [
    status,
    orders,
    availableFilters,
    availableSorts,
    currentPage,
    totalPages,
    totalItems,
    search,
    sortBy,
    sortOrder,
    filters,
    isTodaysStockComplete,
    isMutating,
    errorMessage,
  ];
}

class OrdersCubit extends SafeCubit<OrdersState> {
  final OrdersRepository _repository;

  OrdersCubit({required OrdersRepository repository})
    : _repository = repository,
      super(const OrdersState());

  static const String CLIENT_FILTER = 'client';
  static const int PAGE_SIZE = 10;

  Future<void> loadOrders() => _fetch(page: state.currentPage);

  /// The stock flag rides along with every list load, so verifying an order
  /// (which needs today's count) leaves the chip telling the truth.
  Future<void> loadTodaysStockStatus() async {
    try {
      final bool isComplete = await _repository.fetchTodaysStockComplete();
      emit(state.copyWith(isTodaysStockComplete: isComplete));
    } catch (_) {
      emit(state.copyWith(isTodaysStockComplete: false));
    }
  }

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

  Future<bool> verifyOrder(String publicId) =>
      _mutate(() => _repository.verifyOrder(publicId));

  Future<bool> unverifyOrder(String publicId) =>
      _mutate(() => _repository.unverifyOrder(publicId));

  Future<bool> holdOrder(String publicId) =>
      _mutate(() => _repository.holdOrder(publicId));

  Future<bool> rejectOrder(String publicId) =>
      _mutate(() => _repository.rejectOrder(publicId));

  Future<bool> updateOrder({
    required String publicId,
    required Map<String, dynamic> changes,
  }) {
    if (changes.isEmpty) return Future.value(true);
    return _mutate(
      () => _repository.updateOrder(publicId: publicId, changes: changes),
    );
  }

  Future<OrderModel?> fetchOrder(String publicId) async {
    try {
      return await _repository.fetchOrder(publicId);
    } catch (_) {
      return null;
    }
  }

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
    if (query.isNotEmpty && !params.containsKey(CLIENT_FILTER)) {
      final Set<String> matched = _matchingOptionValues(CLIENT_FILTER, query);
      if (matched.isNotEmpty) params[CLIENT_FILTER] = matched.join(',');
    }

    final String sort = state.sortBy?.trim() ?? '';
    if (sort.isNotEmpty) {
      final bool isDescending =
          (state.sortOrder ?? '') == AppFilterSearchBar.SORT_DESCENDING;
      params['sort'] = isDescending ? '-$sort' : sort;
    }

    return params;
  }

  Set<String> _matchingOptionValues(String filterKey, String term) {
    final ClientFilterModel? filter = _filterFor(filterKey);
    if (filter == null) return const {};

    final String needle = term.toLowerCase();
    return filter.options
        .where((option) => option.label.toLowerCase().contains(needle))
        .map((option) => option.value)
        .toSet();
  }

  Future<void> _fetch({required int page}) async {
    emit(state.copyWith(status: OrdersStatus.loading, clearError: true));
    unawaited(loadTodaysStockStatus());

    try {
      final PaginatedOrdersModel result = await _repository.fetchOrders(
        queryParams: _buildQueryParams(page),
      );

      emit(
        state.copyWith(
          status: OrdersStatus.loaded,
          orders: result.results,
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
        state.copyWith(status: OrdersStatus.failure, errorMessage: e.message),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: OrdersStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
