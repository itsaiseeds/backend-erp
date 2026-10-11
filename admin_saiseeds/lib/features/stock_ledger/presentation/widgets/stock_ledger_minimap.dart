import 'package:intl/intl.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../data/models/stock_ledger_row_model.dart';
import '../bloc/stock_ledger_cubit.dart';
import '../bloc/stock_ledger_state.dart';
import '../chain/stock_ledger_chain_builder.dart';
import '../chain/stock_ledger_event_meta.dart';

/// The left aside: a HEAD→TAIL summary, the vertical minimap of every node,
/// and a static legend explaining the link colours.
///
/// The design's scroll-synced viewport box over the minimap is not built here
/// -- it needs the main chain's live scroll offset and rendered node
/// geometry, which would add a measurement/notification pipeline out of
/// proportion to what it buys the user (the dots and day labels already let
/// an admin orient and jump). Everything else from the design is present:
/// the HEAD/TAIL summary card, per-day labels, per-node coloured dots sized
/// and ringed by selection/highlight state, and the legend.
class StockLedgerMinimap extends StatelessWidget {
  const StockLedgerMinimap({super.key});

  static final NumberFormat _intFormat = NumberFormat('#,##,##0', 'en_IN');

  static String _fmt(num value) => _intFormat.format(value);

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StockLedgerCubit, StockLedgerState>(
      builder: (context, state) {
        final StockLedgerCubit cubit = context.read<StockLedgerCubit>();

        return Container(
          color: AppColors.SURFACE,
          padding: const EdgeInsets.all(AppSpacing.smd),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                AppStrings.STOCK_LEDGER_CHAIN_OVERVIEW,
                style: AppTypography.labelSmall.copyWith(
                  letterSpacing: 0.6,
                  fontSize: 11,
                ),
              ),
              const SizedBox(height: AppSpacing.smd),
              Expanded(
                child: state.isReady && state.rows.isNotEmpty
                    ? _ReadyBody(state: state, cubit: cubit)
                    : _NotReadyBody(state: state),
              ),
              const Divider(height: AppSpacing.lg, color: AppColors.HAIRLINE),
              const _Legend(),
            ],
          ),
        );
      },
    );
  }
}

class _ReadyBody extends StatelessWidget {
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _ReadyBody({required this.state, required this.cubit});

  @override
  Widget build(BuildContext context) {
    final StockLedgerRow opening = state.rows.first;
    final StockLedgerRow closing = state.rows.last;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _SummaryCard(opening: opening, closing: closing, cubit: cubit),
        const SizedBox(height: AppSpacing.smd),
        Expanded(
          child: _MinimapDots(state: state, cubit: cubit),
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final StockLedgerRow opening;
  final StockLedgerRow closing;
  final StockLedgerCubit cubit;

  const _SummaryCard({
    required this.opening,
    required this.closing,
    required this.cubit,
  });

  static final DateFormat _dayFmt = DateFormat('d MMM');

  List<_SummaryLine> _lines() {
    final List<_SummaryLine> lines = [];

    if (opening.bagPools.isNotEmpty) {
      final num openSum = opening.bagPools.fold<num>(
        0,
        (sum, p) => sum + p.figures.available,
      );
      final num closeSum = closing.bagPools.fold<num>(
        0,
        (sum, p) => sum + p.figures.available,
      );
      lines.add(
        _SummaryLine(
          label: AppStrings.STOCK_LEDGER_POOL_BAGS,
          from: StockLedgerMinimap._fmt(openSum),
          to: StockLedgerMinimap._fmt(closeSum),
          negative: closeSum < 0,
        ),
      );
    }
    if (opening.packetPools.isNotEmpty) {
      final num openSum = opening.packetPools.fold<num>(
        0,
        (sum, p) => sum + p.figures.available,
      );
      final num closeSum = closing.packetPools.fold<num>(
        0,
        (sum, p) => sum + p.figures.available,
      );
      lines.add(
        _SummaryLine(
          label: AppStrings.STOCK_LEDGER_POOL_LOOSE,
          from: StockLedgerMinimap._fmt(openSum),
          to: StockLedgerMinimap._fmt(closeSum),
          negative: closeSum < 0,
        ),
      );
    }
    lines.add(
      _SummaryLine(
        label: AppStrings.STOCK_LEDGER_POOL_RAW,
        from: '${StockLedgerMinimap._fmt(opening.rawMaterial.figures.availableValue)} kg',
        to: '${StockLedgerMinimap._fmt(closing.rawMaterial.figures.availableValue)} kg',
        negative: closing.rawMaterial.figures.availableValue < 0,
      ),
    );
    for (final material in closing.otherMaterials) {
      final LedgerOtherMaterial? openMaterial = opening.otherMaterials
          .where((m) => m.materialType.id == material.materialType.id)
          .firstOrNull;
      lines.add(
        _SummaryLine(
          label: material.materialType.name,
          from: StockLedgerMinimap._fmt(
            openMaterial?.figures.availableValue ?? 0,
          ),
          to: StockLedgerMinimap._fmt(material.figures.availableValue),
          negative: material.figures.availableValue < 0,
        ),
      );
    }
    return lines;
  }

  @override
  Widget build(BuildContext context) {
    final String openLabel = opening.occurredAtTime == null
        ? AppStrings.STOCK_LEDGER_HEAD
        : _dayFmt.format(opening.occurredAtTime!.toUtc());
    final String closeLabel = closing.occurredAtTime == null
        ? AppStrings.STOCK_LEDGER_TAIL
        : _dayFmt.format(closing.occurredAtTime!.toUtc());

    return Material(
      color: const Color(0xFFF1F5F3),
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: () => cubit.selectNode(0),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.smd),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.flag_outlined,
                    size: 15,
                    color: AppColors.PRIMARY,
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Flexible(
                    child: Text(
                      '${AppStrings.STOCK_LEDGER_HEAD} · $openLabel → '
                      '${AppStrings.STOCK_LEDGER_TAIL} · $closeLabel',
                      style: AppTypography.labelMedium.copyWith(fontSize: 12),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xs),
              Text(
                AppStrings.STOCK_LEDGER_AVAILABLE,
                style: AppTypography.bodySmall.copyWith(fontSize: 11),
              ),
              const SizedBox(height: 2),
              for (final line in _lines())
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 1.5),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          line.label,
                          style: AppTypography.bodySmall.copyWith(fontSize: 12),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      Text(
                        line.from,
                        style: AppTypography.bodySmall.copyWith(fontSize: 12),
                      ),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 4),
                        child: Icon(
                          Icons.arrow_forward_rounded,
                          size: 11,
                          color: AppColors.TEXT_SECONDARY,
                        ),
                      ),
                      Text(
                        line.to,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: line.negative
                              ? StockLedgerLinkStyle.shrank
                              : AppColors.TEXT_PRIMARY,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SummaryLine {
  final String label;
  final String from;
  final String to;
  final bool negative;

  const _SummaryLine({
    required this.label,
    required this.from,
    required this.to,
    required this.negative,
  });
}

class _MinimapDots extends StatelessWidget {
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _MinimapDots({required this.state, required this.cubit});

  static final DateFormat _dayFmt = DateFormat('d MMM');

  @override
  Widget build(BuildContext context) {
    final StockLedgerChainBuilder builder = StockLedgerChainBuilder(
      rows: state.rows,
      poolFilter: state.poolFilter,
      enabledFamilies: state.enabledFamilies,
      selectedIndex: state.selectedIndex,
      highlightedSourceId: state.highlightedSourceId,
    );
    final List<StockLedgerChainNode> nodes = builder.build();
    final int n = nodes.length;

    final List<_DayLabel> dayLabels = [];
    DateTime? lastDay;
    for (final node in nodes) {
      final DateTime? t = node.row.occurredAtTime?.toUtc();
      if (t == null) continue;
      final DateTime day = DateTime.utc(t.year, t.month, t.day);
      if (day != lastDay) {
        dayLabels.add(
          _DayLabel(top: n <= 1 ? 0 : node.index / (n - 1) * 100, label: _dayFmt.format(day)),
        );
        lastDay = day;
      }
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        const double verticalInset = 9;
        final double trackHeight = (constraints.maxHeight - verticalInset * 2)
            .clamp(0, double.infinity);
        double trackTop(double percent) =>
            verticalInset + (percent / 100) * trackHeight;

        return Stack(
          children: [
            Positioned(
              left: 63,
              top: 0,
              bottom: 0,
              child: Container(width: 2, color: AppColors.BORDER),
            ),
            ValueListenableBuilder<StockLedgerViewportRange>(
              valueListenable: cubit.viewportRange,
              builder: (context, range, _) {
                if (range.height >= 100) return const SizedBox.shrink();
                const double boxOverhang = 9;
                final double top = trackTop(range.top) - boxOverhang;
                final double bottom =
                    trackTop(range.top + range.height) + boxOverhang;
                return Positioned(
                  left: 42,
                  width: 44,
                  top: top,
                  height: (bottom - top).clamp(0, double.infinity),
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: AppColors.PRIMARY.withValues(alpha: 0.08),
                      border: Border.all(
                        color: AppColors.PRIMARY,
                        width: 1.5,
                      ),
                      borderRadius: BorderRadius.circular(7),
                    ),
                  ),
                );
              },
            ),
            for (final day in dayLabels)
              Positioned(
                left: 0,
                top: trackTop(day.top),
                child: FractionalTranslation(
                  translation: const Offset(0, -0.5),
                  child: Text(
                    day.label,
                    style: AppTypography.bodySmall.copyWith(fontSize: 10.5),
                  ),
                ),
              ),
            for (final node in nodes)
              Positioned(
                left: 64 - _dotSize(node, state) / 2,
                top: trackTop(n <= 1 ? 0 : node.index / (n - 1) * 100) -
                    _dotSize(node, state) / 2,
                child: MouseRegion(
                  cursor: SystemMouseCursors.click,
                  child: GestureDetector(
                    onTap: () => cubit.selectNode(node.index),
                    child: Tooltip(
                      message:
                          '${node.meta.title}${StockLedgerMeta.detailLabel(node.row.detail).isNotEmpty ? ' · ${StockLedgerMeta.detailLabel(node.row.detail)}' : ''}',
                      child: Container(
                        width: _dotSize(node, state),
                        height: _dotSize(node, state),
                        decoration: BoxDecoration(
                          color: node.isNegative && !node.isBalance
                              ? StockLedgerLinkStyle.shrank
                              : StockLedgerMeta.families[node.meta.family]!.color,
                          shape: node.row.event == 'ORDER_CONFIRMED' ||
                                  node.row.event == 'ORDER_EDITED' ||
                                  node.row.event == 'ORDER_RELEASED' ||
                                  node.row.event == 'ORDER_DISPATCHED' ||
                                  node.row.event == 'DISPATCH_REVERTED'
                              ? BoxShape.rectangle
                              : BoxShape.circle,
                          borderRadius:
                              node.row.event.startsWith('ORDER') ||
                                      node.row.event == 'DISPATCH_REVERTED'
                                  ? BorderRadius.circular(2)
                                  : null,
                          border: node.isSelected
                              ? Border.all(color: AppColors.PRIMARY, width: 2)
                              : null,
                        ),
                        alignment: Alignment.center,
                        child: Opacity(
                          opacity: !node.isVisible || node.isDimmed ? 0.3 : 1,
                          child: const SizedBox.shrink(),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }

  static double _dotSize(StockLedgerChainNode node, StockLedgerState state) {
    if (node.isBalance) return 12;
    final bool isMember = state.highlightedSourceId != null &&
        node.row.source?.publicId == state.highlightedSourceId;
    return isMember ? 9 : 7;
  }
}

class _DayLabel {
  final double top;
  final String label;

  const _DayLabel({required this.top, required this.label});
}

class _NotReadyBody extends StatelessWidget {
  final StockLedgerState state;

  const _NotReadyBody({required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.start,
      children: [
        const SizedBox(height: 30),
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: AppColors.BORDER_STRONG, width: 2),
          ),
        ),
        Container(
          width: 0,
          height: 200,
          decoration: const BoxDecoration(
            border: Border(
              left: BorderSide(color: AppColors.BORDER, width: 2),
            ),
          ),
        ),
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: AppColors.BORDER_STRONG, width: 2),
          ),
        ),
        const SizedBox(height: AppSpacing.smd),
        Text(
          state.status == StockLedgerStatus.loading
              ? '${AppStrings.STOCK_LEDGER_BUILDING_PREFIX}…'
              : AppStrings.STOCK_LEDGER_MINIMAP_EMPTY,
          style: AppTypography.bodySmall.copyWith(fontSize: 12),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }
}

class _Legend extends StatelessWidget {
  const _Legend();

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.STOCK_LEDGER_LEGEND_TITLE,
          style: AppTypography.labelSmall.copyWith(
            color: AppColors.TEXT_PRIMARY,
            fontSize: 11,
          ),
        ),
        const SizedBox(height: AppSpacing.xs),
        _LegendRow(color: StockLedgerLinkStyle.grew, label: AppStrings.STOCK_LEDGER_LEGEND_GREW),
        _LegendRow(
          color: StockLedgerLinkStyle.shrank,
          label: AppStrings.STOCK_LEDGER_LEGEND_SHRANK,
        ),
        _LegendRow(
          color: AppColors.TEXT_SECONDARY,
          label: AppStrings.STOCK_LEDGER_LEGEND_BOTH,
          hatched: true,
        ),
        _LegendRow(
          color: StockLedgerLinkStyle.unchanged,
          label: AppStrings.STOCK_LEDGER_LEGEND_UNCHANGED,
        ),
      ],
    );
  }
}

class _LegendRow extends StatelessWidget {
  final Color color;
  final String label;
  final bool hatched;

  const _LegendRow({
    required this.color,
    required this.label,
    this.hatched = false,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Container(width: 3, height: 14, color: color),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              label,
              style: AppTypography.bodySmall.copyWith(fontSize: 11.5),
            ),
          ),
        ],
      ),
    );
  }
}

extension on Iterable<LedgerOtherMaterial> {
  LedgerOtherMaterial? get firstOrNull => isEmpty ? null : first;
}
