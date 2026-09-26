import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/inward_raw_materials_repository.dart';
import '../../data/models/inward_raw_material_model.dart';
import '../../data/models/paginated_inward_raw_materials_model.dart';

enum InwardRawMaterialsStatus { initial, loading, loaded, failure }

class InwardRawMaterialsState extends Equatable {
  final InwardRawMaterialsStatus status;
  final List<InwardRawMaterialModel> lots;
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

  const InwardRawMaterialsState({
    this.status = InwardRawMaterialsStatus.initial,
    this.lots = const [],
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

  bool get isEmptySource => (search?.trim().isEmpty ?? true) && filters.isEmpty;

  InwardRawMaterialsState copyWith({
    InwardRawMaterialsStatus? status,
    List<InwardRawMaterialModel>? lots,
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
    return InwardRawMaterialsState(
      status: status ?? this.status,
      lots: lots ?? this.lots,
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

  @override
  List<Object?> get props => [
    status,
    lots,
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

class InwardRawMaterialsCubit extends SafeCubit<InwardRawMaterialsState> {
  final InwardRawMaterialsRepository _repository;

  InwardRawMaterialsCubit({required InwardRawMaterialsRepository repository})
    : _repository = repository,
      super(const InwardRawMaterialsState());

  static const int PAGE_SIZE = 10;
  static const String PRODUCT_FILTER = 'product';

  Future<void> loadLots() => _fetch(page: state.currentPage);

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

  Future<bool> createLot({
    required String productPublicId,
    required int partyId,
    required String quantityKg,
    required String labSamplingDate,
  }) {
    return _mutate(
      () => _repository.createInwardRawMaterial(
        productPublicId: productPublicId,
        partyId: partyId,
        quantityKg: quantityKg,
        labSamplingDate: labSamplingDate,
      ),
    );
  }

  Future<bool> updateLot({
    required String publicId,
    String? labSamplingDate,
    String? status,
  }) {
    return _mutate(
      () => _repository.updateInwardRawMaterial(
        publicId: publicId,
        labSamplingDate: labSamplingDate,
        status: status,
      ),
    );
  }

  Future<bool> deleteLot(String publicId) =>
      _mutate(() => _repository.deleteInwardRawMaterial(publicId));

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

  Map<String, dynamic> _buildQueryParams(int page) {
    final Map<String, dynamic> params = {'page': page, 'page_size': PAGE_SIZE};

    state.filters.forEach((key, value) {
      final String trimmed = value.trim();
      if (trimmed.isEmpty) return;
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

  Future<void> _fetch({required int page}) async {
    emit(
      state.copyWith(
        status: InwardRawMaterialsStatus.loading,
        clearError: true,
      ),
    );

    try {
      final PaginatedInwardRawMaterialsModel result = await _repository
          .fetchInwardRawMaterials(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: InwardRawMaterialsStatus.loaded,
          lots: result.results,
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
          status: InwardRawMaterialsStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: InwardRawMaterialsStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
