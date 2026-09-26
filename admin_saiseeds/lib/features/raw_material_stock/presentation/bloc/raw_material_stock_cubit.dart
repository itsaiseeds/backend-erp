import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/raw_material_stock_model.dart';
import '../../data/raw_material_stock_repository.dart';

enum RawMaterialStockStatus { initial, loading, loaded, failure }

class RawMaterialStockState extends Equatable {
  final RawMaterialStockStatus status;
  final String asOf;
  final List<RawMaterialStockLineModel> allLines;
  final List<RawMaterialStockLineModel> visibleLines;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final String? errorMessage;

  const RawMaterialStockState({
    this.status = RawMaterialStockStatus.initial,
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
      status == RawMaterialStockStatus.loaded && allLines.isEmpty;

  RawMaterialStockState copyWith({
    RawMaterialStockStatus? status,
    String? asOf,
    List<RawMaterialStockLineModel>? allLines,
    List<RawMaterialStockLineModel>? visibleLines,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    String? errorMessage,
    bool clearError = false,
  }) {
    return RawMaterialStockState(
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

class RawMaterialStockCubit extends SafeCubit<RawMaterialStockState> {
  final RawMaterialStockRepository _repository;

  RawMaterialStockCubit({required RawMaterialStockRepository repository})
    : _repository = repository,
      super(const RawMaterialStockState());

  Future<void> loadRawMaterialStock() async {
    emit(
      state.copyWith(status: RawMaterialStockStatus.loading, clearError: true),
    );

    try {
      final RawMaterialStockModel result = await _repository
          .fetchRawMaterialStock();

      emit(
        _projected(
          state.copyWith(
            status: RawMaterialStockStatus.loaded,
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
          status: RawMaterialStockStatus.failure,
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
    final RawMaterialStockState next = RawMaterialStockState(
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

  RawMaterialStockState _projected(
    RawMaterialStockState source, {
    required int page,
  }) {
    final List<RawMaterialStockLineModel> searched =
        ListQuery.search<RawMaterialStockLineModel>(
          source: source.allLines,
          query: source.search,
          searchableValues: (line) => [
            line.name,
            line.incomingKg,
            line.packedKg,
            line.availableKg,
          ],
        );

    final List<RawMaterialStockLineModel> filtered =
        ListQuery.filter<RawMaterialStockLineModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
        );

    final List<RawMaterialStockLineModel> sorted =
        ListQuery.sort<RawMaterialStockLineModel>(
          source: filtered,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<RawMaterialStockLineModel> paged =
        ListQuery.withoutPagination<RawMaterialStockLineModel>(source: sorted);

    return source.copyWith(
      visibleLines: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(RawMaterialStockLineModel line, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_PRODUCT:
        return line.name;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    RawMaterialStockLineModel line,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_PRODUCT:
        return line.name.toLowerCase();
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
