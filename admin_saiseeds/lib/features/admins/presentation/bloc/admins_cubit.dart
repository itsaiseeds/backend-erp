import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/admins_repository.dart';
import '../../data/models/admin_model.dart';

enum AdminsStatus { initial, loading, loaded, failure }

class AdminsState extends Equatable {
  final AdminsStatus status;
  final List<AdminModel> allAdmins;
  final List<AdminModel> visibleAdmins;
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

  const AdminsState({
    this.status = AdminsStatus.initial,
    this.allAdmins = const [],
    this.visibleAdmins = const [],
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

  bool get isEmptySource => status == AdminsStatus.loaded && allAdmins.isEmpty;

  AdminsState copyWith({
    AdminsStatus? status,
    List<AdminModel>? allAdmins,
    List<AdminModel>? visibleAdmins,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isMutating,
    String? errorMessage,
    bool clearError = false,
  }) {
    return AdminsState(
      status: status ?? this.status,
      allAdmins: allAdmins ?? this.allAdmins,
      visibleAdmins: visibleAdmins ?? this.visibleAdmins,
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
    allAdmins,
    visibleAdmins,
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

class AdminsCubit extends SafeCubit<AdminsState> {
  final AdminsRepository _repository;

  AdminsCubit({required AdminsRepository repository})
    : _repository = repository,
      super(const AdminsState());

  Future<void> loadAdmins() async {
    emit(state.copyWith(status: AdminsStatus.loading, clearError: true));

    try {
      final List<AdminModel> admins = await _repository.fetchAdmins();
      emit(
        _projected(
          state.copyWith(
            status: AdminsStatus.loaded,
            allAdmins: admins,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: AdminsStatus.failure,
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
    final AdminsState next = AdminsState(
      status: state.status,
      allAdmins: state.allAdmins,
      visibleAdmins: state.visibleAdmins,
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

  Future<bool> createAdmin({
    required String name,
    required String phoneNumber,
    required int cityId,
    String? email,
  }) async {
    return _mutate(
      () => _repository.createAdmin(
        name: name,
        phoneNumber: phoneNumber,
        cityId: cityId,
        email: email,
      ),
    );
  }

  Future<bool> updateAdmin({
    required String id,
    required String name,
    required String phoneNumber,
    String? email,
  }) async {
    return _mutate(
      () => _repository.updateAdmin(
        id: id,
        name: name,
        phoneNumber: phoneNumber,
        email: email,
      ),
    );
  }

  Future<bool> deleteAdmin(String id) =>
      _mutate(() => _repository.deleteAdmin(id));

  Future<bool> _mutate(Future<void> Function() action) async {
    emit(state.copyWith(isMutating: true, clearError: true));

    try {
      await action();
      emit(state.copyWith(isMutating: false));
      await loadAdmins();
      return true;
    } catch (error) {
      emit(state.copyWith(isMutating: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  AdminsState _projected(AdminsState source, {required int page}) {
    final List<AdminModel> searched = ListQuery.search<AdminModel>(
      source: source.allAdmins,
      query: source.search,
      searchableValues: (admin) => [
        admin.name,
        admin.email,
        admin.phoneNumber,
        admin.role,
        admin.createdByName,
      ],
    );

    final List<AdminModel> filtered = ListQuery.filter<AdminModel>(
      source: searched,
      filters: source.filters,
      fieldValue: _fieldValue,
    );

    final List<AdminModel> sorted = ListQuery.sort<AdminModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<AdminModel> paged =
        ListQuery.withoutPagination<AdminModel>(source: sorted);

    return source.copyWith(
      visibleAdmins: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(AdminModel admin, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_NAME:
        return admin.name;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return admin.phoneNumber;
      case AppStrings.FILTER_BY_ROLE:
        return admin.role;
      case AppStrings.FILTER_BY_EMAIL:
        return admin.email;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(AdminModel admin, String field) {
    switch (field) {
      case AppStrings.SORT_BY_NAME:
        return admin.name.toLowerCase();
      case AppStrings.SORT_BY_EMAIL:
        return admin.email.toLowerCase();
      case AppStrings.SORT_BY_CREATED_AT:
        return admin.createdAt;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
