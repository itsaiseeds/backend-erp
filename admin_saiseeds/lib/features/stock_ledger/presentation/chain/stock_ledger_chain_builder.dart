import 'package:flutter/material.dart';

import '../../../../core/theme/app_colors.dart';
import '../../data/models/stock_ledger_row_model.dart';
import '../bloc/stock_ledger_state.dart';
import 'stock_ledger_event_meta.dart';

/// Which of the four pool groupings a row touched -- drives both the Pool
/// chip filter and "which rows changed this pool" badges.
enum StockLedgerPoolGroup { bags, loose, raw, packing }

StockLedgerPoolGroup? _poolFilterToGroup(StockLedgerPoolFilter f) {
  switch (f) {
    case StockLedgerPoolFilter.bags:
      return StockLedgerPoolGroup.bags;
    case StockLedgerPoolFilter.loose:
      return StockLedgerPoolGroup.loose;
    case StockLedgerPoolFilter.raw:
      return StockLedgerPoolGroup.raw;
    case StockLedgerPoolFilter.packing:
      return StockLedgerPoolGroup.packing;
    case StockLedgerPoolFilter.all:
      return null;
  }
}

/// The net direction of a row's `available` figures across every pool it
/// touched -- what colours the link segment leading into the next row.
enum StockLedgerNetDirection { up, down, mixed, flat }

/// One node, fully resolved against the current filters/selection: whether it
/// is visible, dimmed, selected, and every display value its card needs.
class StockLedgerChainNode {
  final int index;
  final StockLedgerRow row;
  final StockLedgerEventMeta meta;
  final bool isVisible;
  final bool isDimmed;
  final bool isSelected;
  final bool isNegative;
  final Set<StockLedgerPoolGroup> touchedGroups;
  final StockLedgerNetDirection netDirection;

  const StockLedgerChainNode({
    required this.index,
    required this.row,
    required this.meta,
    required this.isVisible,
    required this.isDimmed,
    required this.isSelected,
    required this.isNegative,
    required this.touchedGroups,
    required this.netDirection,
  });

  bool get isBalance => row.isBalance;
}

/// Renders the design's `netBg` colour logic: green when every touched pool's
/// available figure rose, red when it fell, a hatched look when both
/// happened on the same row (a count that raises one packaging and lowers
/// another), grey when nothing moved.
class StockLedgerLinkStyle {
  static const Color grew = Color(0xFF2E8B4F);
  static const Color shrank = Color(0xFFB3482E);
  static const Color unchanged = AppColors.BORDER;

  static Color solidColorFor(StockLedgerNetDirection direction) {
    switch (direction) {
      case StockLedgerNetDirection.up:
        return grew;
      case StockLedgerNetDirection.down:
        return shrank;
      case StockLedgerNetDirection.mixed:
      case StockLedgerNetDirection.flat:
        return unchanged;
    }
  }
}

/// Turns the raw, server-ordered row list into everything the chain widget
/// needs to draw: which nodes are visible under the current filters, the net
/// direction of the link after each node, and per-node touched-pool info.
///
/// Unlike the design mockup (which hand-computes deltas from a dummy event
/// log), every figure here is already on the row from the server -- this
/// class only classifies and filters, it never recomputes a stock number.
class StockLedgerChainBuilder {
  final List<StockLedgerRow> rows;
  final StockLedgerPoolFilter poolFilter;
  final Set<StockLedgerFamily> enabledFamilies;
  final int? selectedIndex;
  final String? highlightedSourceId;

  StockLedgerChainBuilder({
    required this.rows,
    required this.poolFilter,
    required this.enabledFamilies,
    required this.selectedIndex,
    required this.highlightedSourceId,
  });

  late final List<int> highlightedIndexes = highlightedSourceId == null
      ? const []
      : [
          for (int i = 0; i < rows.length; i++)
            if (rows[i].source?.publicId == highlightedSourceId) i,
        ];

  bool get hasHighlight => highlightedIndexes.isNotEmpty;

  Set<StockLedgerPoolGroup> touchedGroupsOf(StockLedgerRow row) {
    final Set<StockLedgerPoolGroup> groups = {};
    if (row.bagPools.any((p) => !p.change.isZero)) {
      groups.add(StockLedgerPoolGroup.bags);
    }
    if (row.packetPools.any((p) => !p.change.isZero)) {
      groups.add(StockLedgerPoolGroup.loose);
    }
    if (!row.rawMaterial.change.isZero) groups.add(StockLedgerPoolGroup.raw);
    if (row.otherMaterials.any((m) => !m.change.isZero)) {
      groups.add(StockLedgerPoolGroup.packing);
    }
    return groups;
  }

  bool isRowVisible(StockLedgerRow row) {
    if (row.isBalance) return true;
    final StockLedgerEventMeta meta = StockLedgerMeta.eventMeta(
      row.event,
      row.detail,
    );
    if (!enabledFamilies.contains(meta.family)) return false;
    final StockLedgerPoolGroup? wanted = _poolFilterToGroup(poolFilter);
    if (wanted == null) return true;
    return touchedGroupsOf(row).contains(wanted);
  }

  bool isRowNegative(StockLedgerRow row) {
    for (final p in row.bagPools) {
      if (p.figures.available < 0) return true;
    }
    for (final p in row.packetPools) {
      if (p.figures.available < 0) return true;
    }
    if (row.rawMaterial.figures.availableValue < 0) return true;
    for (final m in row.otherMaterials) {
      if (m.figures.availableValue < 0) return true;
    }
    return false;
  }

  StockLedgerNetDirection netDirectionOf(StockLedgerRow row) {
    bool up = false, down = false;
    for (final p in row.bagPools) {
      if (p.change.available > 0) up = true;
      if (p.change.available < 0) down = true;
    }
    for (final p in row.packetPools) {
      if (p.change.available > 0) up = true;
      if (p.change.available < 0) down = true;
    }
    final num rawDelta = row.rawMaterial.change.availableValue;
    if (rawDelta > 0) up = true;
    if (rawDelta < 0) down = true;
    for (final m in row.otherMaterials) {
      final num d = m.change.availableValue;
      if (d > 0) up = true;
      if (d < 0) down = true;
    }
    if (up && down) return StockLedgerNetDirection.mixed;
    if (up) return StockLedgerNetDirection.up;
    if (down) return StockLedgerNetDirection.down;
    return StockLedgerNetDirection.flat;
  }

  List<StockLedgerChainNode> build() {
    final List<StockLedgerChainNode> nodes = [];
    for (int i = 0; i < rows.length; i++) {
      final StockLedgerRow row = rows[i];
      final bool visible = isRowVisible(row);
      final bool dimmed = hasHighlight &&
          !row.isBalance &&
          !highlightedIndexes.contains(i);
      nodes.add(
        StockLedgerChainNode(
          index: i,
          row: row,
          meta: StockLedgerMeta.eventMeta(row.event, row.detail),
          isVisible: visible,
          isDimmed: dimmed,
          isSelected: selectedIndex == i,
          isNegative: isRowNegative(row),
          touchedGroups: touchedGroupsOf(row),
          netDirection: netDirectionOf(row),
        ),
      );
    }
    return nodes;
  }

  /// How many consecutive hidden rows precede each visible node -- the
  /// design's "N other events — show" stub between two kept nodes.
  static Map<int, int> hiddenCountsBefore(List<StockLedgerChainNode> nodes) {
    final Map<int, int> hidden = {};
    int running = 0;
    for (final node in nodes) {
      if (!node.isVisible) {
        running++;
        continue;
      }
      if (running > 0) hidden[node.index] = running;
      running = 0;
    }
    return hidden;
  }
}
