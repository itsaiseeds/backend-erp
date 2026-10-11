import 'package:flutter/foundation.dart';
import 'package:intl/intl.dart';

import '../../../../core/bloc/safe_cubit.dart';
import '../../../../core/network/api_exception.dart';
import '../../data/models/stock_ledger_row_model.dart';
import '../../data/stock_ledger_repository.dart';
import 'stock_ledger_state.dart';

/// The vertical slice of the chain's scrollable extent currently visible on
/// screen, as percentages (0-100) of the whole chain -- drives the minimap's
/// scroll-synced viewport box. Lives outside [StockLedgerState] since it
/// changes on every scroll tick and has no business triggering a `BlocBuilder`
/// rebuild of the rest of the screen.
class StockLedgerViewportRange {
  final double top;
  final double height;

  const StockLedgerViewportRange({required this.top, required this.height});

  static const StockLedgerViewportRange full =
      StockLedgerViewportRange(top: 0, height: 100);
}

class StockLedgerCubit extends SafeCubit<StockLedgerState> {
  final StockLedgerRepository _repository;

  StockLedgerCubit({required StockLedgerRepository repository})
    : _repository = repository,
      super(const StockLedgerState());

  final ValueNotifier<StockLedgerViewportRange> viewportRange =
      ValueNotifier(StockLedgerViewportRange.full);

  @override
  Future<void> close() {
    viewportRange.dispose();
    return super.close();
  }

  static final DateFormat _isoDate = DateFormat('yyyy-MM-dd');

  /// Whole range in one request -- the server's own cache already holds every
  /// row for the window, and the browser cache wants the full set too (see
  /// `StockLedgerRepository`), so there is no real pagination left to drive
  /// from the UI.
  static const int _pageSize = 10000;

  Future<void> selectProduct({
    required String publicId,
    required String name,
  }) async {
    emit(
      state.copyWith(
        productPublicId: publicId,
        productName: name,
        status: StockLedgerStatus.idle,
        rows: const [],
        clearSelectedIndex: true,
        clearHighlightedSourceId: true,
        clearGoLiveError: true,
        clearError: true,
      ),
    );
  }

  void setDateRange(DateTime start, DateTime end) {
    emit(state.copyWith(startDate: start, endDate: end));
  }

  Future<void> loadLedger({bool force = false}) async {
    final String? productId = state.productPublicId;
    final DateTime? start = state.startDate;
    final DateTime? end = state.endDate;
    if (productId == null || start == null || end == null) return;

    emit(
      state.copyWith(
        status: StockLedgerStatus.loading,
        clearError: true,
        clearGoLiveError: true,
        clearRateLimitedUntil: true,
        clearSelectedIndex: true,
        clearHighlightedSourceId: true,
      ),
    );

    final int used = await _repository.buildsUsedToday(productId);

    try {
      final StockLedgerResult result = await _repository.fetchLedger(
        productPublicId: productId,
        startDate: _isoDate.format(start),
        endDate: _isoDate.format(end),
        page: 1,
        pageSize: _pageSize,
        force: force,
      );

      final int? openingIndex = result.response.results.isEmpty
          ? null
          : 0;

      emit(
        state.copyWith(
          status: StockLedgerStatus.loaded,
          rows: result.response.results,
          isFromCache: result.fromCache,
          cacheAge: result.cacheAge,
          clearCacheAge: result.cacheAge == null,
          buildsUsedToday: used,
          selectedIndex: openingIndex,
          clearSelectedIndex: openingIndex == null,
        ),
      );
    } on StockLedgerRateLimitedException catch (e) {
      emit(
        state.copyWith(
          status: StockLedgerStatus.rateLimited,
          buildsUsedToday: 2,
          rateLimitedUntil: DateTime.now().add(
            Duration(seconds: e.retryAfterSeconds),
          ),
          errorMessage: e.message,
        ),
      );
    } on ApiException catch (e) {
      if (_isGoLiveError(e)) {
        emit(
          state.copyWith(
            status: StockLedgerStatus.notStarted,
            goLiveError: e.message,
            buildsUsedToday: used,
          ),
        );
        return;
      }
      emit(
        state.copyWith(
          status: StockLedgerStatus.failure,
          errorMessage: e.message,
          buildsUsedToday: used,
        ),
      );
    } catch (_) {
      emit(
        state.copyWith(
          status: StockLedgerStatus.failure,
          errorMessage: 'Something went wrong.',
          buildsUsedToday: used,
        ),
      );
    }
  }

  static bool _isGoLiveError(ApiException e) =>
      e.statusCode == 400 && e.message.toLowerCase().contains('stock ledger starts');

  // ---- Selection / filters ----

  void selectNode(int index) {
    if (index < 0 || index >= state.rows.length) return;
    emit(state.copyWith(selectedIndex: index));
  }

  void selectAdjacent(int delta) {
    final int? current = state.selectedIndex;
    if (current == null) return;
    final int next = (current + delta).clamp(0, state.rows.length - 1);
    emit(state.copyWith(selectedIndex: next));
  }

  void toggleExpanded(int index) {
    final Set<int> next = {...state.expandedIndexes};
    if (!next.add(index)) next.remove(index);
    emit(state.copyWith(expandedIndexes: next));
  }

  void setPoolFilter(StockLedgerPoolFilter filter) {
    emit(state.copyWith(poolFilter: filter));
  }

  void toggleFamily(StockLedgerFamily family) {
    final Set<StockLedgerFamily> next = {...state.enabledFamilies};
    if (!next.add(family)) next.remove(family);
    emit(state.copyWith(enabledFamilies: next));
  }

  void showEverything() {
    emit(
      state.copyWith(
        poolFilter: StockLedgerPoolFilter.all,
        enabledFamilies: const {
          StockLedgerFamily.inward,
          StockLedgerFamily.waste,
          StockLedgerFamily.counts,
          StockLedgerFamily.orders,
          StockLedgerFamily.dispatch,
        },
      ),
    );
  }

  /// Pins (or unpins) every event sharing one source id -- the "Highlight on
  /// chain" / row-level source-chip behaviour.
  void toggleSourceHighlight(String sourceId) {
    if (state.highlightedSourceId == sourceId) {
      emit(state.copyWith(clearHighlightedSourceId: true));
    } else {
      emit(state.copyWith(highlightedSourceId: sourceId));
    }
  }

  void clearSourceHighlight() {
    emit(state.copyWith(clearHighlightedSourceId: true));
  }

  void setHoveredLink(int? index) {
    emit(
      state.copyWith(
        hoveredLinkIndex: index,
        clearHoveredLinkIndex: index == null,
      ),
    );
  }

  void setInspectorOpenOnNarrow(bool open) {
    emit(state.copyWith(inspectorOpenOnNarrow: open));
  }

  /// Every row index sharing [sourceId] -- used both to compute dimming and
  /// to drive the inspector's "Linked events" list.
  List<int> indexesForSource(String sourceId) {
    final List<int> out = [];
    for (int i = 0; i < state.rows.length; i++) {
      final StockLedgerRow row = state.rows[i];
      if (row.source?.publicId == sourceId) out.add(i);
    }
    return out;
  }
}
