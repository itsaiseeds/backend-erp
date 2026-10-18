import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/old_sales_person_model.dart';
import '../../data/sales_people_repository.dart';

enum OldSalesPeopleStatus { initial, loading, loaded, failure }

class OldSalesPeopleState extends Equatable {
  final OldSalesPeopleStatus status;
  final List<OldSalesPersonModel> allSalesPeople;
  final List<OldSalesPersonModel> visibleSalesPeople;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final String? errorMessage;

  const OldSalesPeopleState({
    this.status = OldSalesPeopleStatus.initial,
    this.allSalesPeople = const [],
    this.visibleSalesPeople = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.errorMessage,
  });

  bool get isEmptySource =>
      status == OldSalesPeopleStatus.loaded && allSalesPeople.isEmpty;

  OldSalesPeopleState copyWith({
    OldSalesPeopleStatus? status,
    List<OldSalesPersonModel>? allSalesPeople,
    List<OldSalesPersonModel>? visibleSalesPeople,
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
    return OldSalesPeopleState(
      status: status ?? this.status,
      allSalesPeople: allSalesPeople ?? this.allSalesPeople,
      visibleSalesPeople: visibleSalesPeople ?? this.visibleSalesPeople,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? this.filters,
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
    search,
    sortBy,
    sortOrder,
    filters,
    errorMessage,
  ];
}

class OldSalesPeopleCubit extends SafeCubit<OldSalesPeopleState> {
  final SalesPeopleRepository _repository;

  OldSalesPeopleCubit({required SalesPeopleRepository repository})
    : _repository = repository,
      super(const OldSalesPeopleState());

  Future<void> loadOldSalesPeople() async {
    emit(
      state.copyWith(status: OldSalesPeopleStatus.loading, clearError: true),
    );

    try {
      final List<OldSalesPersonModel> all = await _repository
          .fetchAllSalesPeople();
      final List<OldSalesPersonModel> removed = all
          .where((person) => person.isDeleted)
          .toList();

      emit(
        _projected(
          state.copyWith(
            status: OldSalesPeopleStatus.loaded,
            allSalesPeople: removed,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: OldSalesPeopleStatus.failure,
          errorMessage: _messageOf(error),
        ),
      );
    }
  }

  Future<void> refresh() => loadOldSalesPeople();

  void applyQuery({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    emit(
      _projected(
        state.copyWith(
          search: search,
          sortBy: sortBy,
          sortOrder: sortOrder,
          filters: filters ?? const {},
        ),
        page: page,
      ),
    );
  }

  OldSalesPeopleState _projected(
    OldSalesPeopleState source, {
    required int page,
  }) {
    final List<OldSalesPersonModel> searched =
        ListQuery.search<OldSalesPersonModel>(
          source: source.allSalesPeople,
          query: source.search,
          searchableValues: (person) => [
            person.name,
            person.phoneNumber,
            person.city,
          ],
        );

    final List<OldSalesPersonModel> sorted =
        ListQuery.sort<OldSalesPersonModel>(
          source: searched,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<OldSalesPersonModel> result =
        ListQuery.withoutPagination<OldSalesPersonModel>(source: sorted);

    return source.copyWith(
      visibleSalesPeople: result.items,
      currentPage: result.page,
      totalPages: result.totalPages,
      totalItems: result.totalItems,
    );
  }

  static Comparable<Object>? _sortValue(
    OldSalesPersonModel person,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return person.name.toLowerCase();
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
