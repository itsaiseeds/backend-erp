import 'package:equatable/equatable.dart';

import '../../data/models/stock_ledger_row_model.dart';

enum StockLedgerStatus {
  /// No product chosen yet.
  idle,
  loading,
  loaded,

  /// The window predates go-live -- `LedgerNotStarted` / `goLiveErr` in the
  /// design.
  notStarted,

  /// The server's daily per-product build quota is spent and no cached
  /// window covers this range.
  rateLimited,
  failure,
}

/// The five pool "families" a node's icon/colour is drawn from, same keys the
/// design uses.
enum StockLedgerFamily { inward, waste, counts, orders, dispatch, balance }

/// The four groupings the Pool chip row filters by.
enum StockLedgerPoolFilter { all, bags, loose, raw, packing }

class StockLedgerState extends Equatable {
  final StockLedgerStatus status;

  final String? productPublicId;
  final String? productName;
  final DateTime? startDate;
  final DateTime? endDate;

  final List<StockLedgerRow> rows;
  final String? errorMessage;

  /// From the server's own `LedgerNotStarted` 400 -- "Stock ledger starts on
  /// (date)", shown inline under the date field rather than as a toast.
  final String? goLiveError;

  final bool isFromCache;
  final Duration? cacheAge;

  final DateTime? rateLimitedUntil;

  /// An upper-bound estimate of builds used today for this product (see
  /// `StockLedgerRepository.buildsUsedToday`) -- corrected to the max the
  /// instant a real 429 is seen.
  final int buildsUsedToday;

  // ---- Selection / filter state (mirrors the design's component state) ----

  final int? selectedIndex;
  final Set<int> expandedIndexes;
  final StockLedgerPoolFilter poolFilter;
  final Set<StockLedgerFamily> enabledFamilies;

  /// The source id (e.g. an order's public id) every linked event is
  /// highlighted for, or null when nothing is pinned.
  final String? highlightedSourceId;

  final int? hoveredLinkIndex;
  final bool inspectorOpenOnNarrow;

  const StockLedgerState({
    this.status = StockLedgerStatus.idle,
    this.productPublicId,
    this.productName,
    this.startDate,
    this.endDate,
    this.rows = const [],
    this.errorMessage,
    this.goLiveError,
    this.isFromCache = false,
    this.cacheAge,
    this.rateLimitedUntil,
    this.buildsUsedToday = 0,
    this.selectedIndex,
    this.expandedIndexes = const {},
    this.poolFilter = StockLedgerPoolFilter.all,
    this.enabledFamilies = const {
      StockLedgerFamily.inward,
      StockLedgerFamily.waste,
      StockLedgerFamily.counts,
      StockLedgerFamily.orders,
      StockLedgerFamily.dispatch,
    },
    this.highlightedSourceId,
    this.hoveredLinkIndex,
    this.inspectorOpenOnNarrow = false,
  });

  bool get hasProduct => (productPublicId ?? '').isNotEmpty;

  bool get isReady => status == StockLedgerStatus.loaded;

  int get buildsRemainingToday =>
      (2 - buildsUsedToday).clamp(0, 2); // DAILY_BUILDS_PER_PRODUCT

  StockLedgerRow? get selectedRow =>
      selectedIndex != null && selectedIndex! >= 0 && selectedIndex! < rows.length
      ? rows[selectedIndex!]
      : null;

  StockLedgerState copyWith({
    StockLedgerStatus? status,
    String? productPublicId,
    String? productName,
    DateTime? startDate,
    DateTime? endDate,
    List<StockLedgerRow>? rows,
    String? errorMessage,
    bool clearError = false,
    String? goLiveError,
    bool clearGoLiveError = false,
    bool? isFromCache,
    Duration? cacheAge,
    bool clearCacheAge = false,
    DateTime? rateLimitedUntil,
    bool clearRateLimitedUntil = false,
    int? buildsUsedToday,
    int? selectedIndex,
    bool clearSelectedIndex = false,
    Set<int>? expandedIndexes,
    StockLedgerPoolFilter? poolFilter,
    Set<StockLedgerFamily>? enabledFamilies,
    String? highlightedSourceId,
    bool clearHighlightedSourceId = false,
    int? hoveredLinkIndex,
    bool clearHoveredLinkIndex = false,
    bool? inspectorOpenOnNarrow,
  }) {
    return StockLedgerState(
      status: status ?? this.status,
      productPublicId: productPublicId ?? this.productPublicId,
      productName: productName ?? this.productName,
      startDate: startDate ?? this.startDate,
      endDate: endDate ?? this.endDate,
      rows: rows ?? this.rows,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      goLiveError: clearGoLiveError ? null : (goLiveError ?? this.goLiveError),
      isFromCache: isFromCache ?? this.isFromCache,
      cacheAge: clearCacheAge ? null : (cacheAge ?? this.cacheAge),
      rateLimitedUntil: clearRateLimitedUntil
          ? null
          : (rateLimitedUntil ?? this.rateLimitedUntil),
      buildsUsedToday: buildsUsedToday ?? this.buildsUsedToday,
      selectedIndex: clearSelectedIndex
          ? null
          : (selectedIndex ?? this.selectedIndex),
      expandedIndexes: expandedIndexes ?? this.expandedIndexes,
      poolFilter: poolFilter ?? this.poolFilter,
      enabledFamilies: enabledFamilies ?? this.enabledFamilies,
      highlightedSourceId: clearHighlightedSourceId
          ? null
          : (highlightedSourceId ?? this.highlightedSourceId),
      hoveredLinkIndex: clearHoveredLinkIndex
          ? null
          : (hoveredLinkIndex ?? this.hoveredLinkIndex),
      inspectorOpenOnNarrow: inspectorOpenOnNarrow ?? this.inspectorOpenOnNarrow,
    );
  }

  @override
  List<Object?> get props => [
    status,
    productPublicId,
    productName,
    startDate,
    endDate,
    rows,
    errorMessage,
    goLiveError,
    isFromCache,
    cacheAge,
    rateLimitedUntil,
    buildsUsedToday,
    selectedIndex,
    expandedIndexes,
    poolFilter,
    enabledFamilies,
    highlightedSourceId,
    hoveredLinkIndex,
    inspectorOpenOnNarrow,
  ];
}
