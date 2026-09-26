import 'package:equatable/equatable.dart';
import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/utils/list_query.dart';
import '../../../product_packagings/data/models/product_packaging_model.dart';
import '../../data/models/packet_stock_line_model.dart';
import '../../data/packet_stock_repository.dart';

enum PacketStockStatus { initial, loading, loaded, failure }

class PacketStockState extends Equatable {
  final PacketStockStatus status;
  final String snapshotDate;
  final List<PacketStockLineModel> allLines;
  final List<PacketStockLineModel> visibleLines;
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

  const PacketStockState({
    this.status = PacketStockStatus.initial,
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

  bool get isEmptySource =>
      status == PacketStockStatus.loaded && allLines.isEmpty;

  bool get hasDraft => draftCounts.isNotEmpty;

  bool get isDraftComplete =>
      allLines.isNotEmpty && draftCounts.length >= allLines.length;

  PacketStockState copyWith({
    PacketStockStatus? status,
    String? snapshotDate,
    List<PacketStockLineModel>? allLines,
    List<PacketStockLineModel>? visibleLines,
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
    return PacketStockState(
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

class PacketStockCubit extends SafeCubit<PacketStockState> {
  final PacketStockRepository _repository;

  PacketStockCubit({required PacketStockRepository repository})
    : _repository = repository,
      super(const PacketStockState());

  Future<void> loadPacketStock() async {
    emit(state.copyWith(status: PacketStockStatus.loading, clearError: true));

    try {
      final PacketStockSnapshotModel snapshot = await _repository
          .fetchPacketStock();
      emit(
        _projected(
          state.copyWith(
            status: PacketStockStatus.loaded,
            snapshotDate: snapshot.snapshotDate,
            allLines: _withUncountedPools(snapshot.lines),
            draftCounts: const {},
            clearError: true,
          ),
          page: 1,
        ),
      );
    } catch (error) {
      emit(
        state.copyWith(
          status: PacketStockStatus.failure,
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
    final PacketStockState next = PacketStockState(
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

  void setDraftCount(String poolKey, int? count) {
    if (poolKey.isEmpty) return;

    final Map<String, int> draft = Map<String, int>.from(state.draftCounts);
    if (count == null) {
      draft.remove(poolKey);
    } else {
      draft[poolKey] = count;
    }

    emit(state.copyWith(draftCounts: draft));
  }

  void clearDraft() => emit(state.copyWith(draftCounts: const {}));

  Future<bool> submitDraft() async {
    final List<PacketStockCountEntry> entries = _draftEntries();
    if (entries.isEmpty) return false;

    emit(state.copyWith(isSubmitting: true, clearError: true));

    try {
      if (state.isDraftComplete) {
        await _repository.replacePacketStock(entries);
      } else {
        await _repository.patchPacketStock(entries);
      }
      emit(state.copyWith(isSubmitting: false, draftCounts: const {}));
      await loadPacketStock();
      return true;
    } catch (error) {
      emit(state.copyWith(isSubmitting: false, errorMessage: _messageOf(error)));
      return false;
    }
  }

  List<PacketStockLineModel> _withUncountedPools(
    List<PacketStockLineModel> lines,
  ) {
    final PackagingsService service = PackagingsService.instance;
    if (!service.isLoaded) return lines;

    final Map<String, PacketStockLineModel> pools = {};

    for (final PacketStockLineModel line in lines) {
      pools[line.poolKey] = line;
    }

    for (final ProductPackagingModel packaging in service.packagings) {
      final String key = PacketStockLineModel.poolKeyOf(
        packaging.productPublicId,
        packaging.packetWeight,
      );
      final PacketStockLineModel? existing = pools[key];

      if (existing == null) {
        pools[key] = PacketStockLineModel(
          product: PacketStockProductRef(
            publicId: packaging.productPublicId,
            name: packaging.productName,
          ),
          packetWeight: packaging.packetWeight,
        );
        continue;
      }

      if (existing.productName.trim().isNotEmpty) continue;

      pools[key] = PacketStockLineModel(
        product: PacketStockProductRef(
          publicId: existing.productPublicId,
          name: packaging.productName,
        ),
        packetWeight: existing.packetWeight,
        onHand: existing.onHand,
        reserved: existing.reserved,
        consumed: existing.consumed,
        available: existing.available,
      );
    }

    return pools.values.toList();
  }

  List<PacketStockCountEntry> _draftEntries() {
    final List<PacketStockCountEntry> entries = [];

    for (final PacketStockLineModel line in state.allLines) {
      final int? count = state.draftCounts[line.poolKey];
      if (count == null) continue;

      entries.add(
        PacketStockCountEntry(
          productPublicId: line.productPublicId,
          packetWeight: line.packetWeight,
          packets: count,
        ),
      );
    }

    return entries;
  }

  PacketStockState _projected(PacketStockState source, {required int page}) {
    final List<PacketStockLineModel> searched =
        ListQuery.search<PacketStockLineModel>(
          source: source.allLines,
          query: source.search,
          searchableValues: (line) => [
            line.productName,
            line.packetWeight,
            '${line.onHand}',
            '${line.available}',
          ],
        );

    final List<PacketStockLineModel> filtered =
        ListQuery.filter<PacketStockLineModel>(
          source: searched,
          filters: source.filters,
          fieldValue: _fieldValue,
        );

    final List<PacketStockLineModel> sorted =
        ListQuery.sort<PacketStockLineModel>(
          source: filtered,
          sortBy: source.sortBy,
          sortOrder: source.sortOrder,
          sortValue: _sortValue,
        );

    final ListQueryResult<PacketStockLineModel> paged =
        ListQuery.withoutPagination<PacketStockLineModel>(source: sorted);

    return source.copyWith(
      visibleLines: paged.items,
      currentPage: paged.page,
      totalPages: paged.totalPages,
      totalItems: paged.totalItems,
    );
  }

  static String? _fieldValue(PacketStockLineModel line, String field) {
    switch (field) {
      case AppStrings.FILTER_BY_PRODUCT:
        return line.productName;
      default:
        return null;
    }
  }

  static Comparable<Object>? _sortValue(
    PacketStockLineModel line,
    String field,
  ) {
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
