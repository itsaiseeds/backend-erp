import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/godown_managers_repository.dart';
import '../../data/models/godown_manager_model.dart';

enum GodownManagersStatus { initial, loading, loaded, failure }

class GodownManagersState extends Equatable {
  final GodownManagersStatus status;
  final List<GodownManagerModel> allGodownManagers;
  final List<GodownManagerModel> visibleGodownManagers;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final bool isMutating;
  final String? errorMessage;

  const GodownManagersState({
    this.status = GodownManagersStatus.initial,
    this.allGodownManagers = const [],
    this.visibleGodownManagers = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.limit = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.isMutating = false,
    this.errorMessage,
  });

  bool get isEmptySource =>
      status == GodownManagersStatus.loaded && allGodownManagers.isEmpty;

  GodownManagersState copyWith({
    GodownManagersStatus? status,
    List<GodownManagerModel>? allGodownManagers,
    List<GodownManagerModel>? visibleGodownManagers,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return GodownManagersState(
      status: status ?? this.status,
      allGodownManagers: allGodownManagers ?? this.allGodownManagers,
      visibleGodownManagers:
          visibleGodownManagers ?? this.visibleGodownManagers,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      limit: limit ?? this.limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? this.filters,
      isMutating: isMutating ?? this.isMutating,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
    status,
    allGodownManagers,
    visibleGodownManagers,
    currentPage,
    totalPages,
    totalItems,
    limit,
    search,
    sortBy,
    sortOrder,
    filters,
    isMutating,
    errorMessage,
  ];
}

class GodownManagersCubit extends SafeCubit<GodownManagersState> {
  final GodownManagersRepository _repository;

  GodownManagersCubit({required GodownManagersRepository repository})
    : _repository = repository,
      super(const GodownManagersState());

  Future<void> loadGodownManagers() async {
    emit(
      state.copyWith(status: GodownManagersStatus.loading, clearError: true),
    );

    try {
      final List<GodownManagerModel> managers = await _repository
          .fetchGodownManagers();
      emit(
        _projected(
          state.copyWith(
            status: GodownManagersStatus.loaded,
            allGodownManagers: managers,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: GodownManagersStatus.failure,
          errorMessage: _messageOf(error),
        ),
      );
    }
  }

  void applyQuery({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    final GodownManagersState next = GodownManagersState(
      status: state.status,
      allGodownManagers: state.allGodownManagers,
      visibleGodownManagers: state.visibleGodownManagers,
      currentPage: state.currentPage,
      totalPages: state.totalPages,
      totalItems: state.totalItems,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? const {},
      isMutating: state.isMutating,
      errorMessage: state.errorMessage,
    );

    emit(_projected(next, page: page));
  }

  Future<bool> createGodownManager({
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    return _mutate(
      () => _repository.createGodownManager(
        name: name,
        phoneNumber: phoneNumber,
        email: email,
      ),
    );
  }

  Future<bool> updateGodownManager({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    return _mutate(
      () => _repository.updateGodownManager(
        id: id,
        name: name,
        phoneNumber: phoneNumber,
        email: email,
      ),
    );
  }

  Future<bool> deleteGodownManager(String id) =>
      _mutate(() => _repository.deleteGodownManager(id));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadGodownManagers();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  GodownManagersState _projected(
    GodownManagersState source, {
    required int page,
  }) {
    final List<GodownManagerModel> searched =
        ListQuery.search<GodownManagerModel>(
          source: source.allGodownManagers,
          query: source.search,
          searchableValues: (manager) => [
            manager.name,
            manager.email,
            manager.phoneNumber,
            manager.createdByName,
          ],
        );

    final List<GodownManagerModel> filtered =
        ListQuery.filter<GodownManagerModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
        );

    final List<GodownManagerModel> sorted = ListQuery.sort<GodownManagerModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<GodownManagerModel> paged =
        ListQuery.withoutPagination<GodownManagerModel>(source: sorted);

    return source.copyWith(
      visibleGodownManagers: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(GodownManagerModel manager, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_NAME:
        return manager.name;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return manager.phoneNumber;
      case AppStrings.FILTER_BY_EMAIL:
        return manager.email;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    GodownManagerModel manager,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return manager.name.toLowerCase();
      case AppStrings.SORT_BY_EMAIL:
        return manager.email.toLowerCase();
      case AppStrings.SORT_BY_CREATED_AT:
        return manager.createdAt;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
