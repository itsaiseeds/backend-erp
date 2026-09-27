import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/other_material_stock_model.dart';
import '../../data/other_material_stock_repository.dart';

enum OtherMaterialStockStatus { initial, loading, loaded, failure }

class OtherMaterialStockState extends Equatable {
  final OtherMaterialStockStatus status;
  final String asOf;
  final List<OtherMaterialStockLineModel> allLines;
  final List<OtherMaterialStockLineModel> visibleLines;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final String? errorMessage;

  const OtherMaterialStockState({
    this.status = OtherMaterialStockStatus.initial,
    this.asOf = '',
    this.allLines = const [],
    this.visibleLines = const [],
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.limit = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.errorMessage,
  });

  bool get isEmptySource =>
      status == OtherMaterialStockStatus.loaded && allLines.isEmpty;

  OtherMaterialStockState copyWith({
    OtherMaterialStockStatus? status,
    String? asOf,
    List<OtherMaterialStockLineModel>? allLines,
    List<OtherMaterialStockLineModel>? visibleLines,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    String? errorMessage,
    bool clearError = false,
  }) {
    return OtherMaterialStockState(
      status: status ?? this.status,
      asOf: asOf ?? this.asOf,
      allLines: allLines ?? this.allLines,
      visibleLines: visibleLines ?? this.visibleLines,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      limit: limit ?? this.limit,
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
    asOf,
    allLines,
    visibleLines,
    currentPage,
    totalPages,
    totalItems,
    limit,
    search,
    sortBy,
    sortOrder,
    filters,
    errorMessage,
  ];
}

class OtherMaterialStockCubit extends SafeCubit<OtherMaterialStockState> {
  final OtherMaterialStockRepository _repository;

  OtherMaterialStockCubit({required OtherMaterialStockRepository repository})
    : _repository = repository,
      super(const OtherMaterialStockState());

  Future<void> loadOtherMaterialStock() async {
    emit(
      state.copyWith(status: OtherMaterialStockStatus.loading, clearError: true),
    );

    try {
      final OtherMaterialStockModel result = await _repository
          .fetchOtherMaterialStock();

      emit(
        _projected(
          state.copyWith(
            status: OtherMaterialStockStatus.loaded,
            asOf: result.asOf,
            allLines: result.lines,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: OtherMaterialStockStatus.failure,
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
    final OtherMaterialStockState next = OtherMaterialStockState(
      status: state.status,
      asOf: state.asOf,
      allLines: state.allLines,
      visibleLines: state.visibleLines,
      currentPage: state.currentPage,
      totalPages: state.totalPages,
      totalItems: state.totalItems,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? const {},
      errorMessage: state.errorMessage,
    );

    emit(_projected(next, page: page));
  }

  OtherMaterialStockState _projected(
    OtherMaterialStockState source, {
    required int page,
  }) {
    final List<OtherMaterialStockLineModel> searched =
        ListQuery.search<OtherMaterialStockLineModel>(
          source: source.allLines,
          query: source.search,
          searchableValues: (line) => [
            line.materialTypeName,
            line.unitType,
            line.onHand,
          ],
        );

    final List<OtherMaterialStockLineModel> filtered =
        ListQuery.filter<OtherMaterialStockLineModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
          exactFields: const {AppStrings.FILTER_BY_MATERIAL_TYPE},
        );

    final List<OtherMaterialStockLineModel> sorted =
        ListQuery.sort<OtherMaterialStockLineModel>(
          source: filtered,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<OtherMaterialStockLineModel> paged =
        ListQuery.withoutPagination<OtherMaterialStockLineModel>(
          source: sorted,
        );

    return source.copyWith(
      visibleLines: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(OtherMaterialStockLineModel line, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_MATERIAL_TYPE:
        return line.materialTypeName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    OtherMaterialStockLineModel line,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_MATERIAL_TYPE:
        return line.materialTypeName.toLowerCase();
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
