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
import '../chain/stock_ledger_event_meta.dart';

final NumberFormat _intFmt = NumberFormat('#,##,##0', 'en_IN');
String _fmt(num v) => _intFmt.format(v);
String _signed(num v) => v > 0 ? '+${_fmt(v)}' : (v < 0 ? _fmt(v) : '0');

/// The right aside: full detail on the currently-selected node, with
/// prev/next navigation, the linked-events list (when its source touches
/// more than one row) and every pool's before→after figures.
class StockLedgerInspector extends StatelessWidget {
  final bool narrow;

  const StockLedgerInspector({super.key, required this.narrow});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StockLedgerCubit, StockLedgerState>(
      builder: (context, state) {
        final StockLedgerCubit cubit = context.read<StockLedgerCubit>();
        final StockLedgerRow? row = state.selectedRow;

        return Container(
          color: AppColors.SURFACE,
          child: row == null
              ? _NoSelection(state: state)
              : _Selected(
                  row: row,
                  index: state.selectedIndex!,
                  total: state.rows.length,
                  state: state,
                  cubit: cubit,
                  narrow: narrow,
                ),
        );
      },
    );
  }
}

class _NoSelection extends StatelessWidget {
  final StockLedgerState state;

  const _NoSelection({required this.state});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            AppStrings.STOCK_LEDGER_INSPECTOR,
            style: AppTypography.labelSmall.copyWith(letterSpacing: 0.6, fontSize: 11),
          ),
          const SizedBox(height: AppSpacing.xxl),
          Center(
            child: Text(
              state.status == StockLedgerStatus.loading
                  ? AppStrings.STOCK_LEDGER_SELECT_WHEN_LOADED
                  : AppStrings.STOCK_LEDGER_NO_SELECTION,
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium.copyWith(
                fontSize: 13,
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Selected extends StatelessWidget {
  final StockLedgerRow row;
  final int index;
  final int total;
  final StockLedgerState state;
  final StockLedgerCubit cubit;
  final bool narrow;

  const _Selected({
    required this.row,
    required this.index,
    required this.total,
    required this.state,
    required this.cubit,
    required this.narrow,
  });

  String get _position {
    if (row.isOpening) return AppStrings.STOCK_LEDGER_HEAD;
    if (row.isClosing) return AppStrings.STOCK_LEDGER_TAIL;
    return '#$index of ${total - 2}';
  }

  @override
  Widget build(BuildContext context) {
    final meta = StockLedgerMeta.families[StockLedgerMeta.eventMeta(row.event, row.detail).family]!;
    final String detailLabel = StockLedgerMeta.detailLabel(row.detail);
    final List<int> linked = row.source == null
        ? const []
        : cubit.indexesForSource(row.source!.publicId);

    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(20, 18, 20, 40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                AppStrings.STOCK_LEDGER_INSPECTOR,
                style: AppTypography.labelSmall.copyWith(letterSpacing: 0.6, fontSize: 11),
              ),
              if (narrow) ...[
                const SizedBox(width: AppSpacing.sm),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 18),
                  color: AppColors.TEXT_SECONDARY,
                  padding: EdgeInsets.zero,
                  constraints: const BoxConstraints(minWidth: 24, minHeight: 24),
                  onPressed: () => cubit.setInspectorOpenOnNarrow(false),
                ),
              ],
              const Spacer(),
              Text(
                _position,
                style: const TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              _NavButton(
                icon: Icons.keyboard_arrow_up_rounded,
                onTap: index > 0 ? () => cubit.selectAdjacent(-1) : null,
              ),
              const SizedBox(width: AppSpacing.xs),
              _NavButton(
                icon: Icons.keyboard_arrow_down_rounded,
                onTap: index < total - 1 ? () => cubit.selectAdjacent(1) : null,
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: meta.tint,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                alignment: Alignment.center,
                child: Icon(meta.icon, size: 22, color: meta.color),
              ),
              const SizedBox(width: AppSpacing.smd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      StockLedgerMeta.eventMeta(row.event, row.detail).title,
                      style: AppTypography.titleMedium.copyWith(fontSize: 16),
                    ),
                    if (detailLabel.isNotEmpty || row.isBalance)
                      Text(
                        row.isBalance
                            ? (row.isOpening
                                ? 'Start of range'
                                : 'End of range')
                            : detailLabel,
                        style: TextStyle(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w500,
                          color: meta.color,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.md),
          Container(
            padding: const EdgeInsets.all(AppSpacing.smd),
            decoration: BoxDecoration(
              color: const Color(0xFFF6F8F7),
              borderRadius: BorderRadius.circular(AppRadius.lg),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _InfoRow(
                  label: AppStrings.STOCK_LEDGER_OCCURRED,
                  value: row.occurredAtTime == null
                      ? '—'
                      : DateFormat('yyyy-MM-dd HH:mm:ss').format(row.occurredAtTime!.toUtc()),
                  mono: true,
                ),
                if (row.source != null) ...[
                  _InfoRow(
                    label: AppStrings.STOCK_LEDGER_SOURCE,
                    value: StockLedgerMeta.sourceKindMeta(row.source!.kind).$1,
                  ),
                  _InfoRow(
                    label: AppStrings.STOCK_LEDGER_ID,
                    value: row.source!.publicId,
                    mono: true,
                  ),
                  _InfoRow(
                    label: AppStrings.STOCK_LEDGER_LABEL,
                    value: row.source!.label,
                  ),
                ],
                _InfoRow(
                  label: AppStrings.STOCK_LEDGER_ACTOR,
                  value: row.isBalance
                      ? '—'
                      : (row.actor?.name ?? AppStrings.STOCK_LEDGER_AUTOMATIC_ACTOR),
                ),
              ],
            ),
          ),
          if (linked.length > 1) ...[
            const SizedBox(height: AppSpacing.md),
            _LinkedEvents(
              row: row,
              linked: linked,
              state: state,
              cubit: cubit,
            ),
          ],
          if (!row.isBalance && _hasAnyPoolChange(row)) ...[
            const SizedBox(height: AppSpacing.md),
            Text(
              AppStrings.STOCK_LEDGER_BEFORE_AFTER,
              style: AppTypography.labelMedium.copyWith(fontSize: 12),
            ),
            const SizedBox(height: AppSpacing.sm),
            ..._changedPoolCards(row),
          ],
          const SizedBox(height: AppSpacing.md),
          Text(
            row.isBalance
                ? AppStrings.STOCK_LEDGER_AVAILABLE_BY_POOL
                : AppStrings.STOCK_LEDGER_UNTOUCHED_POOLS,
            style: AppTypography.labelMedium.copyWith(fontSize: 12),
          ),
          const SizedBox(height: AppSpacing.xs),
          ..._untouchedRows(row),
        ],
      ),
    );
  }

  static bool _hasAnyPoolChange(StockLedgerRow row) {
    if (row.bagPools.any((p) => !p.change.isZero)) return true;
    if (row.packetPools.any((p) => !p.change.isZero)) return true;
    if (!row.rawMaterial.change.isZero) return true;
    if (row.otherMaterials.any((m) => !m.change.isZero)) return true;
    return false;
  }

  static List<Widget> _changedPoolCards(StockLedgerRow row) {
    final List<Widget> cards = [];

    for (final p in row.bagPools) {
      if (p.change.isZero) continue;
      cards.add(_PoolCard(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_BAGS,
        sub: '${p.packaging.packetWeight} kg × ${p.packaging.packets}',
        fields: [
          (AppStrings.STOCK_LEDGER_FIELD_ON_HAND, p.figures.onHand - p.change.onHand, p.figures.onHand, p.change.onHand),
          (AppStrings.STOCK_LEDGER_FIELD_RESERVED, p.figures.reserved - p.change.reserved, p.figures.reserved, p.change.reserved),
          (AppStrings.STOCK_LEDGER_FIELD_CONSUMED, p.figures.consumed - p.change.consumed, p.figures.consumed, p.change.consumed),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, p.figures.available - p.change.available, p.figures.available, p.change.available),
        ],
      ));
    }
    for (final p in row.packetPools) {
      if (p.change.isZero) continue;
      cards.add(_PoolCard(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_LOOSE,
        sub: '${p.packetWeight} kg',
        fields: [
          (AppStrings.STOCK_LEDGER_FIELD_ON_HAND, p.figures.onHand - p.change.onHand, p.figures.onHand, p.change.onHand),
          (AppStrings.STOCK_LEDGER_FIELD_RESERVED, p.figures.reserved - p.change.reserved, p.figures.reserved, p.change.reserved),
          (AppStrings.STOCK_LEDGER_FIELD_CONSUMED, p.figures.consumed - p.change.consumed, p.figures.consumed, p.change.consumed),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, p.figures.available - p.change.available, p.figures.available, p.change.available),
        ],
      ));
    }
    if (!row.rawMaterial.change.isZero) {
      final r = row.rawMaterial;
      cards.add(_PoolCard(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_RAW,
        sub: 'kg',
        fields: [
          (AppStrings.STOCK_LEDGER_FIELD_INCOMING, r.figures.incomingValue - r.change.incomingValue, r.figures.incomingValue, r.change.incomingValue),
          (AppStrings.STOCK_LEDGER_FIELD_PACKED, r.figures.packedValue - r.change.packedValue, r.figures.packedValue, r.change.packedValue),
          (AppStrings.STOCK_LEDGER_FIELD_REJECTED, r.figures.rejectedValue - r.change.rejectedValue, r.figures.rejectedValue, r.change.rejectedValue),
          (AppStrings.STOCK_LEDGER_FIELD_WASTED, r.figures.wastedValue - r.change.wastedValue, r.figures.wastedValue, r.change.wastedValue),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, r.figures.availableValue - r.change.availableValue, r.figures.availableValue, r.change.availableValue),
        ],
      ));
    }
    for (final m in row.otherMaterials) {
      if (m.change.isZero) continue;
      cards.add(_PoolCard(
        name: m.materialType.name,
        sub: m.materialType.unitType,
        fields: [
          (AppStrings.STOCK_LEDGER_FIELD_INCOMING, m.figures.incomingValue - m.change.incomingValue, m.figures.incomingValue, m.change.incomingValue),
          (AppStrings.STOCK_LEDGER_FIELD_PACKED, m.figures.packedValue - m.change.packedValue, m.figures.packedValue, m.change.packedValue),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, m.figures.availableValue - m.change.availableValue, m.figures.availableValue, m.change.availableValue),
        ],
      ));
    }

    return cards;
  }

  List<Widget> _untouchedRows(StockLedgerRow row) {
    final List<Widget> rows = [];

    bool bagChanged(int i) => !row.bagPools[i].change.isZero;
    for (int i = 0; i < row.bagPools.length; i++) {
      if (!row.isBalance && bagChanged(i)) continue;
      final p = row.bagPools[i];
      rows.add(_UntouchedRow(
        name: '${AppStrings.STOCK_LEDGER_POOL_NAME_BAGS} · ${p.packaging.packetWeight} kg',
        value: _fmt(p.figures.available),
        negative: p.figures.available < 0,
      ));
    }
    for (final p in row.packetPools) {
      if (!row.isBalance && !p.change.isZero) continue;
      rows.add(_UntouchedRow(
        name: '${AppStrings.STOCK_LEDGER_POOL_NAME_LOOSE} · ${p.packetWeight} kg',
        value: _fmt(p.figures.available),
        negative: p.figures.available < 0,
      ));
    }
    if (row.isBalance || row.rawMaterial.change.isZero) {
      rows.add(_UntouchedRow(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_RAW,
        value: '${_fmt(row.rawMaterial.figures.availableValue)} kg',
        negative: row.rawMaterial.figures.availableValue < 0,
      ));
    }
    for (final m in row.otherMaterials) {
      if (!row.isBalance && !m.change.isZero) continue;
      rows.add(_UntouchedRow(
        name: m.materialType.name,
        value: _fmt(m.figures.availableValue),
        negative: m.figures.availableValue < 0,
      ));
    }

    return rows;
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _NavButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 28,
      height: 28,
      child: OutlinedButton(
        onPressed: onTap,
        style: OutlinedButton.styleFrom(
          padding: EdgeInsets.zero,
          side: const BorderSide(color: AppColors.BORDER),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.sm)),
        ),
        child: Icon(icon, size: 18, color: AppColors.TEXT_PRIMARY),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  final bool mono;

  const _InfoRow({required this.label, required this.value, this.mono = false});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: AppTypography.bodySmall.copyWith(fontSize: 12.5)),
          const Spacer(),
          Flexible(
            child: Text(
              value.isEmpty ? '—' : value,
              textAlign: TextAlign.end,
              style: TextStyle(
                fontSize: 12.5,
                fontFamily: mono ? 'monospace' : null,
                color: AppColors.TEXT_PRIMARY,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LinkedEvents extends StatelessWidget {
  final StockLedgerRow row;
  final List<int> linked;
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _LinkedEvents({
    required this.row,
    required this.linked,
    required this.state,
    required this.cubit,
  });

  @override
  Widget build(BuildContext context) {
    final bool highlighted = state.highlightedSourceId == row.source!.publicId;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              '${AppStrings.STOCK_LEDGER_LINKED_EVENTS} · ${linked.length}',
              style: AppTypography.labelMedium.copyWith(fontSize: 12),
            ),
            const Spacer(),
            OutlinedButton(
              onPressed: () => cubit.toggleSourceHighlight(row.source!.publicId),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size(0, 26),
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                backgroundColor: highlighted ? AppColors.PRIMARY : AppColors.SURFACE,
                side: const BorderSide(color: AppColors.PRIMARY),
                foregroundColor: highlighted ? AppColors.TEXT_ON_PRIMARY : AppColors.PRIMARY,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.sm)),
              ),
              child: Text(
                highlighted
                    ? AppStrings.STOCK_LEDGER_CLEAR_HIGHLIGHT
                    : AppStrings.STOCK_LEDGER_HIGHLIGHT_ON_CHAIN,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        for (final i in linked)
          _LinkedEventTile(
            row: state.rows[i],
            isSelected: i == state.selectedIndex,
            onTap: () => cubit.selectNode(i),
          ),
      ],
    );
  }
}

class _LinkedEventTile extends StatelessWidget {
  final StockLedgerRow row;
  final bool isSelected;
  final VoidCallback onTap;

  const _LinkedEventTile({
    required this.row,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final meta = StockLedgerMeta.families[StockLedgerMeta.eventMeta(row.event, row.detail).family]!;
    final String time = row.occurredAtTime == null
        ? ''
        : DateFormat('d MMM · HH:mm').format(row.occurredAtTime!.toUtc().add(const Duration(hours: 5, minutes: 30)));

    return Material(
      color: isSelected ? const Color(0xFFEEF3F0) : Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs, vertical: 5),
          child: Row(
            children: [
              Container(
                width: 12,
                height: 12,
                decoration: BoxDecoration(
                  color: meta.color,
                  shape: BoxShape.circle,
                  border: Border.all(color: AppColors.SURFACE, width: 2),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                StockLedgerMeta.eventMeta(row.event, row.detail).title,
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              Expanded(
                child: Text(
                  StockLedgerMeta.detailLabel(row.detail),
                  style: AppTypography.bodySmall.copyWith(fontSize: 12),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                time,
                style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: AppColors.TEXT_SECONDARY),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PoolCard extends StatelessWidget {
  final String name;
  final String sub;
  final List<(String, num, num, num)> fields;

  const _PoolCard({required this.name, required this.sub, required this.fields});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd, vertical: AppSpacing.sm),
      decoration: BoxDecoration(
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text.rich(
            TextSpan(
              children: [
                TextSpan(
                  text: name,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                ),
                TextSpan(
                  text: ' $sub',
                  style: AppTypography.bodySmall.copyWith(fontSize: 11.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xs),
          for (final (label, from, to, delta) in fields)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                children: [
                  Expanded(
                    child: Text(label, style: AppTypography.bodySmall.copyWith(fontSize: 12.5)),
                  ),
                  Text(
                    '${_fmt(from)} → ',
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: delta != 0 ? FontWeight.w600 : FontWeight.w400,
                    ),
                  ),
                  Text(
                    _fmt(to),
                    style: TextStyle(
                      fontSize: 12.5,
                      fontWeight: delta != 0 ? FontWeight.w600 : FontWeight.w400,
                      color: to < 0 ? const Color(0xFFAC3A1F) : AppColors.TEXT_PRIMARY,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Container(
                    constraints: const BoxConstraints(minWidth: 44),
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: delta > 0
                          ? const Color(0xFFE3F3E6)
                          : (delta < 0 ? const Color(0xFFF7E3DD) : AppColors.SURFACE_VARIANT),
                      borderRadius: BorderRadius.circular(5),
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _signed(delta),
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: delta > 0
                            ? const Color(0xFF237A39)
                            : (delta < 0 ? const Color(0xFFAC3A1F) : AppColors.TEXT_SECONDARY),
                      ),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _UntouchedRow extends StatelessWidget {
  final String name;
  final String value;
  final bool negative;

  const _UntouchedRow({required this.name, required this.value, required this.negative});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 4),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.HAIRLINE)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(name, style: AppTypography.bodySmall.copyWith(fontSize: 12.5)),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 12.5,
              color: negative ? const Color(0xFFAC3A1F) : AppColors.TEXT_PRIMARY,
            ),
          ),
        ],
      ),
    );
  }
}
