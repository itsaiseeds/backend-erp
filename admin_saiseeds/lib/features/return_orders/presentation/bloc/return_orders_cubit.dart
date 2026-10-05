import 'dart:async';

import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/paginated_return_orders_model.dart';
import '../../data/models/return_order_edit_model.dart';
import '../../data/models/return_order_model.dart';
import '../../data/models/return_order_status.dart';
import '../../data/models/return_recipe_model.dart';
import '../../data/return_orders_repository.dart';

enum ReturnOrdersStatus { initial, loading, loaded, failure }

class ReturnOrdersState extends Equatable {
  final ReturnOrdersStatus status;
  final List<ReturnOrderModel> returnOrders;
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

  /// Pending is the default because the admin's job is the queue of returns
  /// waiting on a decision, not the archive of settled ones.
  const ReturnOrdersState({
    this.status = ReturnOrdersStatus.initial,
    this.returnOrders = const [],
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {
      ReturnOrdersCubit.STATUS_FILTER: ReturnOrderStatusX.PENDING,
    },
    this.isMutating = false,
    this.errorMessage,
  });

  ReturnOrdersState copyWith({
    ReturnOrdersStatus? status,
    List<ReturnOrderModel>? returnOrders,
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
    return ReturnOrdersState(
      status: status ?? this.status,
      returnOrders: returnOrders ?? this.returnOrders,
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

  bool get isEmptySource =>
      status == ReturnOrdersStatus.loaded && returnOrders.isEmpty;

  bool get hasMore => currentPage < totalPages;

  @override
  List<Object?> get props => [
    status,
    returnOrders,
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

class ReturnOrdersCubit extends SafeCubit<ReturnOrdersState> {
  final ReturnOrdersRepository _repository;

  ReturnOrdersCubit({required ReturnOrdersRepository repository})
    : _repository = repository,
      super(const ReturnOrdersState());

  static const String STATUS_FILTER = 'status';
  static const String CLIENT_FILTER = 'client';
  static const String ORDER_FILTER = 'order';
  static const int PAGE_SIZE = 10;

  Future<void> loadReturnOrders() => _fetch(page: state.currentPage);

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
        filters: filters ?? state.filters,
      ),
    );
    await _fetch(page: page);
  }

  Future<bool> acceptReturn({
    required String publicId,
    required bool includeInOtherRawMaterials,
    required List<String> recipePublicIds,
  }) {
    return _mutate(
      () => _repository.acceptReturn(
        publicId: publicId,
        includeInOtherRawMaterials: includeInOtherRawMaterials,
        recipePublicIds: recipePublicIds,
      ),
    );
  }

  Future<bool> rejectReturn(String publicId) =>
      _mutate(() => _repository.rejectReturn(publicId));

  Future<bool> unrejectReturn(String publicId) =>
      _mutate(() => _repository.unrejectReturn(publicId));

  Future<bool> revertAcceptReturn(String publicId) =>
      _mutate(() => _repository.revertAcceptReturn(publicId));

  Future<bool> updateReturn({
    required String publicId,
    required ReturnOrderEditRequest request,
  }) {
    if (request.items.isEmpty) return Future.value(false);
    return _mutate(
      () => _repository.updateReturn(publicId: publicId, request: request),
    );
  }

  /// Loaded by the accept dialog rather than the table, so a failure here shows
  /// up in the dialog instead of an error toast behind it.
  Future<ReturnOrderRecipesModel?> fetchRecipes(String publicId) async {
    try {
      return await _repository.fetchRecipes(publicId);
    } catch (e) {
      emit(state.copyWith(errorMessage: _messageOf(e)));
      return null;
    }
  }

  /// Pulls the next page and appends it, for scroll-to-load.
  Future<void> loadMore() async {
    if (!state.hasMore) return;
    if (state.status == ReturnOrdersStatus.loading) return;
    await _fetch(page: state.currentPage + 1, append: true);
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

    // The search box is free text, and the list endpoint only speaks ids, so a
    // term is resolved against the client and order options the backend ships.
    final String query = state.search?.trim() ?? '';
    if (query.isNotEmpty) {
      if (!params.containsKey(CLIENT_FILTER)) {
        final Set<String> matched = _matchingOptionValues(CLIENT_FILTER, query);
        if (matched.isNotEmpty) params[CLIENT_FILTER] = matched.join(',');
      }
      if (!params.containsKey(ORDER_FILTER)) {
        final Set<String> matched = _matchingOptionValues(ORDER_FILTER, query);
        if (matched.isNotEmpty) params[ORDER_FILTER] = matched.join(',');
      }
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

  static String _messageOf(Object error) {
    if (error is ApiException) return error.message;
    return AppStrings.SOMETHING_WENT_WRONG;
  }

  Future<void> _fetch({required int page, bool append = false}) async {
    emit(state.copyWith(status: ReturnOrdersStatus.loading, clearError: true));

    try {
      final PaginatedReturnOrdersModel result = await _repository
          .fetchReturnOrders(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: ReturnOrdersStatus.loaded,
          returnOrders: append
              ? [...state.returnOrders, ...result.results]
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
          status: ReturnOrdersStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: ReturnOrdersStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
