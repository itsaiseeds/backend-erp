import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../../orders/data/models/order_status.dart';
import '../../data/custom_orders_repository.dart';
import '../../data/models/custom_order_model.dart';
import '../../data/models/paginated_custom_orders_model.dart';

enum CustomOrdersStatus { initial, loading, loaded, failure }

class CustomOrdersState extends Equatable {
  final CustomOrdersStatus status;
  final List<CustomOrderModel> orders;
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

  const CustomOrdersState({
    this.status = CustomOrdersStatus.initial,
    this.orders = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {
      CustomOrdersCubit.STATUS_FILTER: OrderStatusX.CONFIRMED,
    },
    this.isMutating = false,
    this.errorMessage,
  });

  CustomOrdersState copyWith({
    CustomOrdersStatus? status,
    List<CustomOrderModel>? orders,
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
    return CustomOrdersState(
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
      isMutating: isMutating ?? this.isMutating,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  bool get hasMore => currentPage < totalPages;

  bool get isEmptySource => (search?.trim().isEmpty ?? true) && filters.isEmpty;

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
    isMutating,
    errorMessage,
  ];
}

class CustomOrdersCubit extends SafeCubit<CustomOrdersState> {
  final CustomOrdersRepository _repository;

  CustomOrdersCubit({required CustomOrdersRepository repository})
    : _repository = repository,
      super(const CustomOrdersState());

  static const int PAGE_SIZE = 10;
  static const String STATUS_FILTER = 'status';

  Future<void> loadCustomOrders() => _fetch(page: state.currentPage);

  Future<void> refresh() => _fetch(page: state.currentPage);

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

  Future<CustomOrderModel?> fetchCustomOrder(String publicId) async {
    try {
      return await _repository.fetchCustomOrder(publicId);
    } catch (_) {
      return null;
    }
  }

  Future<bool> createCustomOrder(Map<String, dynamic> body) =>
      _mutate(() => _repository.createCustomOrder(body));

  Future<bool> updateCustomOrder({
    required String publicId,
    required Map<String, dynamic> changes,
  }) {
    if (changes.isEmpty) return Future.value(true);
    return _mutate(
      () => _repository.updateCustomOrder(publicId: publicId, changes: changes),
    );
  }

  Future<bool> deleteCustomOrder(String publicId) =>
      _mutate(() => _repository.deleteCustomOrder(publicId));

  Future<bool> dispatchCustomOrder({
    required String publicId,
    required Map<String, dynamic> body,
  }) {
    return _mutate(
      () => _repository.dispatchCustomOrder(publicId: publicId, body: body),
    );
  }

  Future<bool> revertDispatch(String publicId) =>
      _mutate(() => _repository.revertDispatch(publicId));

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
    if (state.status == CustomOrdersStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
  }

  Future<void> _fetch({required int page, bool append = false}) async {
    emit(state.copyWith(status: CustomOrdersStatus.loading, clearError: true));

    try {
      final PaginatedCustomOrdersModel result = await _repository
          .fetchCustomOrders(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: CustomOrdersStatus.loaded,
          orders: append
              ? [...state.orders, ...result.results]
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
          status: CustomOrdersStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: CustomOrdersStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
