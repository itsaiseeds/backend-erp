import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/lab_testers_repository.dart';
import '../../data/models/lab_tester_model.dart';

enum LabTestersStatus { initial, loading, loaded, failure }

class LabTestersState extends Equatable {
  final LabTestersStatus status;
  final List<LabTesterModel> allLabTesters;
  final List<LabTesterModel> visibleLabTesters;
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

  const LabTestersState({
    this.status = LabTestersStatus.initial,
    this.allLabTesters = const [],
    this.visibleLabTesters = const [],
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
      status == LabTestersStatus.loaded && allLabTesters.isEmpty;

  LabTestersState copyWith({
    LabTestersStatus? status,
    List<LabTesterModel>? allLabTesters,
    List<LabTesterModel>? visibleLabTesters,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return LabTestersState(
      status: status ?? this.status,
      allLabTesters: allLabTesters ?? this.allLabTesters,
      visibleLabTesters: visibleLabTesters ?? this.visibleLabTesters,
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
    allLabTesters,
    visibleLabTesters,
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

class LabTestersCubit extends SafeCubit<LabTestersState> {
  final LabTestersRepository _repository;

  LabTestersCubit({required LabTestersRepository repository})
    : _repository = repository,
      super(const LabTestersState());

  Future<void> loadLabTesters() async {
    emit(state.copyWith(status: LabTestersStatus.loading, clearError: true));

    try {
      final List<LabTesterModel> testers = await _repository.fetchLabTesters();
      emit(
        _projected(
          state.copyWith(
            status: LabTestersStatus.loaded,
            allLabTesters: testers,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: LabTestersStatus.failure,
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
    final LabTestersState next = LabTestersState(
      status: state.status,
      allLabTesters: state.allLabTesters,
      visibleLabTesters: state.visibleLabTesters,
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

  Future<bool> createLabTester({
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    return _mutate(
      () => _repository.createLabTester(
        name: name,
        phoneNumber: phoneNumber,
        email: email,
      ),
    );
  }

  Future<bool> updateLabTester({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    return _mutate(
      () => _repository.updateLabTester(
        id: id,
        name: name,
        phoneNumber: phoneNumber,
        email: email,
      ),
    );
  }

  Future<bool> deleteLabTester(String id) =>
      _mutate(() => _repository.deleteLabTester(id));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadLabTesters();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  LabTestersState _projected(LabTestersState source, {required int page}) {
    final List<LabTesterModel> searched = ListQuery.search<LabTesterModel>(
      source: source.allLabTesters,
      query: source.search,
      searchableValues: (tester) => [
        tester.name,
        tester.email,
        tester.phoneNumber,
        tester.createdByName,
      ],
    );

    final List<LabTesterModel> filtered = ListQuery.filter<LabTesterModel>(
      source: searched,
      filters: source.filters,
      fieldValue: _fieldValue,
    );

    final List<LabTesterModel> sorted = ListQuery.sort<LabTesterModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<LabTesterModel> paged =
        ListQuery.withoutPagination<LabTesterModel>(source: sorted);

    return source.copyWith(
      visibleLabTesters: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(LabTesterModel tester, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_NAME:
        return tester.name;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return tester.phoneNumber;
      case AppStrings.FILTER_BY_EMAIL:
        return tester.email;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(LabTesterModel tester, String field) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return tester.name.toLowerCase();
      case AppStrings.SORT_BY_EMAIL:
        return tester.email.toLowerCase();
      case AppStrings.SORT_BY_CREATED_AT:
        return tester.createdAt;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
