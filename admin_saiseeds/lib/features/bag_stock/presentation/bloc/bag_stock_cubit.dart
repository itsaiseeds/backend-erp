import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/utils/list_query.dart';
import '../../data/bag_stock_repository.dart';
import '../../data/models/bag_stock_line_model.dart';

enum BagStockStatus { initial, loading, loaded, failure }

class BagStockState extends Equatable {
  final BagStockStatus status;
  final String snapshotDate;
  final List<BagStockLineModel> allLines;
  final List<BagStockLineModel> visibleLines;
  final Map<String, int> draftCounts;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final int limit;
  final String? search;
  final String? sortBy;
  final String? sortOrder;
  final Map<String, String> filters;
  final bool isSubmitting;
  final String? errorMessage;

  const BagStockState({
    this.status = BagStockStatus.initial,
    this.snapshotDate = '',
    this.allLines = const [],
    this.visibleLines = const [],
    this.draftCounts = const {},
    this.currentPage = 1,
    this.totalPages = 0,
    this.totalItems = 0,
    this.limit = 0,
    this.search,
    this.sortBy,
    this.sortOrder,
    this.filters = const {},
    this.isSubmitting = false,
    this.errorMessage,
  });

  bool get isEmptySource => status == BagStockStatus.loaded && allLines.isEmpty;

  bool get hasDraft => draftCounts.isNotEmpty;

  bool get isDraftComplete =>
      allLines.isNotEmpty && draftCounts.length >= allLines.length;

  BagStockState copyWith({
    BagStockStatus? status,
    String? snapshotDate,
    List<BagStockLineModel>? allLines,
    List<BagStockLineModel>? visibleLines,
    Map<String, int>? draftCounts,
    int? currentPage,
    int? totalPages,
    int? totalItems,
    int? limit,
    Map<String, String>? filters,
    bool? isSubmitting,
    String? errorMessage,
    bool clearError = false,
  }) {
    return BagStockState(
      status: status ?? this.status,
      snapshotDate: snapshotDate ?? this.snapshotDate,
      allLines: allLines ?? this.allLines,
      visibleLines: visibleLines ?? this.visibleLines,
      draftCounts: draftCounts ?? this.draftCounts,
      currentPage: currentPage ?? this.currentPage,
      totalPages: totalPages ?? this.totalPages,
      totalItems: totalItems ?? this.totalItems,
      limit: limit ?? this.limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? this.filters,
      isSubmitting: isSubmitting ?? this.isSubmitting,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
    );
  }

  @override
  List<Object?> get props => [
    status,
    snapshotDate,
    allLines,
    visibleLines,
    draftCounts,
    currentPage,
    totalPages,
    totalItems,
    limit,
    search,
    sortBy,
    sortOrder,
    filters,
    isSubmitting,
    errorMessage,
  ];
}

class BagStockCubit extends SafeCubit<BagStockState> {
  final BagStockRepository _repository;

  BagStockCubit({required BagStockRepository repository})
    : _repository = repository,
      super(const BagStockState());

  Future<void> loadBagStock() async {
    emit(state.copyWith(status: BagStockStatus.loading, clearError: true));

    try {
      final BagStockSnapshotModel snapshot = await _repository.fetchBagStock();
      emit(
        _projected(
          state.copyWith(
            status: BagStockStatus.loaded,
            snapshotDate: snapshot.snapshotDate,
            allLines: _withUncountedPackagings(snapshot.lines),
            draftCounts: const {},
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: BagStockStatus.failure,
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
    final BagStockState next = BagStockState(
      status: state.status,
      snapshotDate: state.snapshotDate,
      allLines: state.allLines,
      visibleLines: state.visibleLines,
      draftCounts: state.draftCounts,
      currentPage: state.currentPage,
      totalPages: state.totalPages,
      totalItems: state.totalItems,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters ?? const {},
      isSubmitting: state.isSubmitting,
      errorMessage: state.errorMessage,
    );

    emit(_projected(next, page: page));
  }

  void setDraftCount(String packagingPublicId, int? count) {
    if (packagingPublicId.isEmpty) return;

    final Map<String, int> draft = Map<String, int>.from(state.draftCounts);
    if (count == null) {
      draft.remove(packagingPublicId);
    } else {
      draft[packagingPublicId] = count;
    }

    emit(state.copyWith(draftCounts: draft));
  }

  void clearDraft() => emit(state.copyWith(draftCounts: const {}));

  Future<bool> submitDraft() async {
    final Map<String, int> draft = Map<String, int>.from(state.draftCounts);
    if (draft.isEmpty) return false;

    emit(state.copyWith(isSubmitting: true, clearError: true));

    try {
      if (state.isDraftComplete) {
        await _repository.replaceBagStock(draft);
      } else {
        await _repository.patchBagStock(draft);
      }
      emit(state.copyWith(isSubmitting: false, draftCounts: const {}));
      await loadBagStock();
      return true;
    } catch (error) {
      emit(state.copyWith(isSubmitting: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  List<BagStockLineModel> _withUncountedPackagings(
    List<BagStockLineModel> lines,
  ) {
    final PackagingsService service = PackagingsService.instance;
    if (!service.isLoaded) return lines;

    final Map<String, BagStockLineModel> counted = {
      for (final BagStockLineModel line in lines)
        if (line.packagingPublicId.isNotEmpty) line.packagingPublicId: line,
    };

    return service.packagings.map((packaging) {
      final BagStockLineModel? line = counted.remove(packaging.publicId);
      if (line == null) return BagStockLineModel(packaging: packaging);

      return BagStockLineModel(
        packaging: packaging,
        onHand: line.onHand,
        reserved: line.reserved,
        consumed: line.consumed,
        available: line.available,
      );
    }).toList()..addAll(counted.values);
  }

  BagStockState _projected(BagStockState source, {required int page}) {
    final List<BagStockLineModel> searched = ListQuery.search<BagStockLineModel>(
      source: source.allLines,
      query: source.search,
      searchableValues: (line) => [
        line.productName,
        line.packetWeight,
        '${line.onHand}',
        '${line.available}',
      ],
    );

    final List<BagStockLineModel> filtered = ListQuery.filter<BagStockLineModel>(
      source: searched,
      filters: source.filters,
      fieldValue: _fieldValue,
    );

    final List<BagStockLineModel> sorted = ListQuery.sort<BagStockLineModel>(
      source: filtered,
      sortBy: source.sortBy,
      sortOrder: source.sortOrder,
      sortValue: _sortValue,
    );

    final ListQueryResult<BagStockLineModel> paged =
        ListQuery.withoutPagination<BagStockLineModel>(source: sorted);

    return source.copyWith(
      visibleLines: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(BagStockLineModel line, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_PRODUCT:
        return line.productName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(BagStockLineModel line, String field) {
    switch (field) {
      case AppStrings.SORT_BY_PRODUCT:
        return line.productName.toLowerCase();
      case AppStrings.SORT_BY_PACKET_WEIGHT:
        return line.packetWeightValue;
      default:
        return null;
    }
  }

  static String _messageOf(Object error) =>
      error is ApiException ? error.message : AppStrings.SOMETHING_WENT_WRONG;
}
