import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/sales_person_model.dart';
import '../../data/sales_people_repository.dart';

enum SalesPeopleStatus { initial, loading, loaded, failure }

class SalesPeopleState extends Equatable {
  final SalesPeopleStatus status;
  final List<SalesPersonModel> allSalesPeople;
  final List<SalesPersonModel> visibleSalesPeople;
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

  const SalesPeopleState({
    this.status = SalesPeopleStatus.initial,
    this.allSalesPeople = const [],
    this.visibleSalesPeople = const [],
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
      status == SalesPeopleStatus.loaded && allSalesPeople.isEmpty;

  SalesPeopleState copyWith({
    SalesPeopleStatus? status,
    List<SalesPersonModel>? allSalesPeople,
    List<SalesPersonModel>? visibleSalesPeople,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return SalesPeopleState(
      status: status ?? this.status,
      allSalesPeople: allSalesPeople ?? this.allSalesPeople,
      visibleSalesPeople: visibleSalesPeople ?? this.visibleSalesPeople,
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
    allSalesPeople,
    visibleSalesPeople,
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

class SalesPeopleCubit extends SafeCubit<SalesPeopleState> {
  final SalesPeopleRepository _repository;

  SalesPeopleCubit({required SalesPeopleRepository repository})
    : _repository = repository,
      super(const SalesPeopleState());

  Future<void> loadSalesPeople() async {
    emit(state.copyWith(status: SalesPeopleStatus.loading, clearError: true));

    try {
      final List<SalesPersonModel> salesPeople = await _repository
          .fetchSalesPeople();
      emit(
        _projected(
          state.copyWith(
            status: SalesPeopleStatus.loaded,
            allSalesPeople: salesPeople,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: SalesPeopleStatus.failure,
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
    final SalesPeopleState next = SalesPeopleState(
      status: state.status,
      allSalesPeople: state.allSalesPeople,
      visibleSalesPeople: state.visibleSalesPeople,
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

  Future<bool> createSalesPerson({
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    return _mutate(
      () => _repository.createSalesPerson(
        name: name,
        phoneNumber: phoneNumber,
        cityId: cityId,
        email: email,
      ),
    );
  }

  Future<bool> updateSalesPerson({
    required String id,
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    return _mutate(
      () => _repository.updateSalesPerson(
        id: id,
        name: name,
        phoneNumber: phoneNumber,
        cityId: cityId,
        email: email,
      ),
    );
  }

  Future<bool> deleteSalesPerson(String id) =>
      _mutate(() => _repository.deleteSalesPerson(id));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadSalesPeople();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  SalesPeopleState _projected(
    SalesPeopleState source, {
    required int page,
  }) {
    final List<SalesPersonModel> searched = ListQuery.search<SalesPersonModel>(
      source: source.allSalesPeople,
      query: source.search,
      searchableValues: (person) => [
        person.name,
        person.email,
        person.phoneNumber,
        person.cityName,
        person.createdByName,
      ],
    );

    final List<SalesPersonModel> filtered = ListQuery.filter<SalesPersonModel>(
      source: searched,
      filters: source.filters,
      fieldValue: _fieldValue,
    );

    final List<SalesPersonModel> sorted = ListQuery.sort<SalesPersonModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<SalesPersonModel> paged =
        ListQuery.withoutPagination<SalesPersonModel>(
          source: sorted,
        );

    return source.copyWith(
      visibleSalesPeople: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(SalesPersonModel person, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_NAME:
        return person.name;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return person.phoneNumber;
      case AppStrings.FILTER_BY_EMAIL:
        return person.email;
      case AppStrings.FILTER_BY_CITY:
        return person.cityName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    SalesPersonModel person,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return person.name.toLowerCase();
      case AppStrings.SORT_BY_EMAIL:
        return person.email.toLowerCase();
      case AppStrings.SORT_BY_CREATED_AT:
        return person.createdAt;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) => error is ApiException
      ? error.message
      : AppStrings.SOMETHING_WENT_WRONG;
}
