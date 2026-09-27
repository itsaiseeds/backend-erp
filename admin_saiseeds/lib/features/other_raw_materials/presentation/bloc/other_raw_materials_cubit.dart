import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/other_material_recipe_model.dart';
import '../../data/models/paginated_other_material_recipes_model.dart';
import '../../data/other_raw_materials_repository.dart';

enum OtherRawMaterialsStatus { initial, loading, loaded, failure }

class OtherRawMaterialsState extends Equatable {
  final OtherRawMaterialsStatus status;
  final List<OtherMaterialRecipeModel> recipes;
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

  const OtherRawMaterialsState({
    this.status = OtherRawMaterialsStatus.initial,
    this.recipes = const [],
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

  OtherRawMaterialsState copyWith({
    OtherRawMaterialsStatus? status,
    List<OtherMaterialRecipeModel>? recipes,
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
    return OtherRawMaterialsState(
      status: status ?? this.status,
      recipes: recipes ?? this.recipes,
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
    recipes,
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

class OtherRawMaterialsCubit extends SafeCubit<OtherRawMaterialsState> {
  final OtherRawMaterialsRepository _repository;

  OtherRawMaterialsCubit({required OtherRawMaterialsRepository repository})
    : _repository = repository,
      super(const OtherRawMaterialsState());

  static const int PAGE_SIZE = 10;

  Future<void> loadRecipes() => _fetch(page: state.currentPage);

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

  Future<bool> createRecipe({
    required String productPublicId,
    required int materialTypeId,
    required String packetWeight,
    required String quantity,
  }) {
    return _mutate(
      () => _repository.createRecipe(
        productPublicId: productPublicId,
        materialTypeId: materialTypeId,
        packetWeight: packetWeight,
        quantity: quantity,
      ),
    );
  }

  Future<bool> deleteRecipe(String publicId) =>
      _mutate(() => _repository.deleteRecipe(publicId));

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
      state.copyWith(status: OtherRawMaterialsStatus.loading, clearError: true),
    );

    try {
      final PaginatedOtherMaterialRecipesModel result = await _repository
          .fetchRecipes(queryParams: _buildQueryParams(page));

      emit(
        state.copyWith(
          status: OtherRawMaterialsStatus.loaded,
          recipes: result.results,
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
          status: OtherRawMaterialsStatus.failure,
          errorMessage: e.message,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: OtherRawMaterialsStatus.failure,
          errorMessage: AppStrings.SOMETHING_WENT_WRONG,
        ),
      );
    }
  }
}
