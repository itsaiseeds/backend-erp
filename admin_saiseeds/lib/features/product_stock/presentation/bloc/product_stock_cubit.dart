import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/models/product_stock_line_model.dart';
import '../../data/product_stock_repository.dart';

enum ProductStockStatus { initial, loading, loaded, failure }

class ProductStockState extends Equatable {
  final ProductStockStatus status;
  final List<ProductStockLineModel> allLines;
  final List<ProductStockLineModel> visibleLines;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final String? errorMessage;

  const ProductStockState({
    this.status = ProductStockStatus.initial,
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
      status == ProductStockStatus.loaded && allLines.isEmpty;

  String get snapshotDate {
    for (final ProductStockLineModel line in allLines) {
      if (line.snapshotDate.trim().isNotEmpty) return line.snapshotDate;
    }
    return '';
  }

  ProductStockState copyWith({
    ProductStockStatus? status,
    List<ProductStockLineModel>? allLines,
    List<ProductStockLineModel>? visibleLines,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    String? errorMessage,
    bool clearError = false,
  }) {
    return ProductStockState(
      status: status ?? this.status,
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

class ProductStockCubit extends SafeCubit<ProductStockState> {
  final ProductStockRepository _repository;

  ProductStockCubit({required ProductStockRepository repository})
    : _repository = repository,
      super(const ProductStockState());

  Future<void> loadProductStock() async {
    emit(state.copyWith(status: ProductStockStatus.loading, clearError: true));

    try {
      final List<ProductStockLineModel> lines = await _repository.fetchAll();

      emit(
        _projected(
          state.copyWith(
            status: ProductStockStatus.loaded,
            allLines: lines,
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: ProductStockStatus.failure,
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
    final ProductStockState next = ProductStockState(
      status: state.status,
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

  ProductStockState _projected(ProductStockState source, {required int page}) {
    final List<ProductStockLineModel> searched =
        ListQuery.search<ProductStockLineModel>(
          source: source.allLines,
          query: source.search,
          searchableValues: (line) => [
            line.name,
            line.packetWeight,
            '${line.onHand}',
            '${line.available}',
          ],
        );

    final List<ProductStockLineModel> filtered =
        ListQuery.filter<ProductStockLineModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
        );

    final List<ProductStockLineModel> sorted =
        ListQuery.sort<ProductStockLineModel>(
          source: filtered,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<ProductStockLineModel> paged =
        ListQuery.withoutPagination<ProductStockLineModel>(source: sorted);

    return source.copyWith(
      visibleLines: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(ProductStockLineModel line, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_PRODUCT:
        return line.name;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    ProductStockLineModel line,
    String field,
  ) {
    switch (field) {
      case AppStrings.SORT_BY_PRODUCT:
        return line.name.toLowerCase();
      case AppStrings.SORT_BY_PACKET_WEIGHT:
        return line.packetWeightValue;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
