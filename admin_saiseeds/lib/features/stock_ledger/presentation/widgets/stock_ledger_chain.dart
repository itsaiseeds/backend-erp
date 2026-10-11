import 'package:intl/intl.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../data/models/stock_ledger_row_model.dart';
import '../bloc/stock_ledger_cubit.dart';
import '../bloc/stock_ledger_state.dart';
import '../chain/stock_ledger_chain_builder.dart';
import '../chain/stock_ledger_event_meta.dart';

final NumberFormat _intFmt = NumberFormat('#,##,##0', 'en_IN');
String _fmt(num v) => _intFmt.format(v);
String _signed(num v) => v > 0 ? '+${_fmt(v)}' : (v < 0 ? _fmt(v) : '0');

/// The main scrollable area: pool/event filters, the "following X" banner,
/// the vertical event chain itself, and every non-chain state (loading
/// skeleton, no-events, empty illustration, rate-limited / not-started
/// banners).
class StockLedgerChain extends StatelessWidget {
  const StockLedgerChain({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StockLedgerCubit, StockLedgerState>(
      builder: (context, state) {
        final StockLedgerCubit cubit = context.read<StockLedgerCubit>();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (state.status == StockLedgerStatus.rateLimited)
              const _DailyLimitBanner(),
            if (state.status == StockLedgerStatus.notStarted)
              const _NotStartedBanner(),
            if (state.isReady) ...[
              _ChainToolbar(state: state, cubit: cubit),
              if (state.highlightedSourceId != null)
                _FollowingBar(state: state, cubit: cubit),
            ],
            Expanded(
              child: ScrollConfiguration(
                behavior: ScrollConfiguration.of(
                  context,
                ).copyWith(scrollbars: false),
                child: _ChainBody(state: state, cubit: cubit),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _DailyLimitBanner extends StatelessWidget {
  const _DailyLimitBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.smd, AppSpacing.xl, 0),
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: BoxDecoration(
        color: const Color(0xFFFCF3E6),
        border: Border.all(color: const Color(0xFFEBCFA0)),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.block_rounded, size: 20, color: Color(0xFFAD6A1F)),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: AppTypography.bodyMedium.copyWith(fontSize: 13.5, height: 1.4),
                children: [
                  TextSpan(
                    text: '${AppStrings.STOCK_LEDGER_DAILY_LIMIT_TITLE} ',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  TextSpan(text: AppStrings.STOCK_LEDGER_DAILY_LIMIT_BODY),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _NotStartedBanner extends StatelessWidget {
  const _NotStartedBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(AppSpacing.xl, AppSpacing.smd, AppSpacing.xl, 0),
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: BoxDecoration(
        color: const Color(0xFFEEF2FB),
        border: Border.all(color: const Color(0xFFCBD7F2)),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded, size: 20, color: Color(0xFF3D6FC9)),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: RichText(
              text: TextSpan(
                style: AppTypography.bodyMedium.copyWith(fontSize: 13.5),
                children: [
                  TextSpan(
                    text: '${AppStrings.STOCK_LEDGER_NOT_STARTED_TITLE} ',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  TextSpan(text: AppStrings.STOCK_LEDGER_NOT_STARTED_BODY),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChainToolbar extends StatelessWidget {
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _ChainToolbar({required this.state, required this.cubit});

  static final DateFormat _dayFmt = DateFormat('EEE d MMM yyyy');

  @override
  Widget build(BuildContext context) {
    final int eventCount = state.rows.where((r) => !r.isBalance).length;
    final DateTime? start = state.rows.isNotEmpty
        ? state.rows.first.occurredAtTime?.toUtc()
        : null;
    final DateTime? end = state.rows.isNotEmpty
        ? state.rows.last.occurredAtTime?.toUtc()
        : null;
    final String sub = start != null && end != null
        ? '$eventCount events · ${_dayFmt.format(start)} – ${_dayFmt.format(end)}'
        : '$eventCount events';

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xl,
        vertical: AppSpacing.smd,
      ),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: AppColors.BORDER)),
      ),
      child: Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: AppSpacing.md,
        runSpacing: AppSpacing.sm,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                state.productName ?? '',
                style: AppTypography.titleMedium.copyWith(fontSize: 15),
              ),
              Text(sub, style: AppTypography.bodySmall.copyWith(fontSize: 12)),
            ],
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                AppStrings.STOCK_LEDGER_POOL_LABEL,
                style: AppTypography.bodySmall.copyWith(fontSize: 12),
              ),
              const SizedBox(width: AppSpacing.sm),
              Container(
                padding: const EdgeInsets.all(3),
                decoration: BoxDecoration(
                  color: const Color(0xFFE7EBE9),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (final f in StockLedgerPoolFilter.values)
                      _PoolChip(
                        filter: f,
                        isActive: state.poolFilter == f,
                        onTap: () => cubit.setPoolFilter(f),
                      ),
                  ],
                ),
              ),
            ],
          ),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: AppSpacing.xs,
            children: [
              Text(
                AppStrings.STOCK_LEDGER_EVENTS_LABEL,
                style: AppTypography.bodySmall.copyWith(fontSize: 12),
              ),
              for (final family in const [
                StockLedgerFamily.inward,
                StockLedgerFamily.waste,
                StockLedgerFamily.counts,
                StockLedgerFamily.orders,
                StockLedgerFamily.dispatch,
              ])
                _FamilyChip(
                  family: family,
                  isActive: state.enabledFamilies.contains(family),
                  onTap: () => cubit.toggleFamily(family),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PoolChip extends StatelessWidget {
  final StockLedgerPoolFilter filter;
  final bool isActive;
  final VoidCallback onTap;

  const _PoolChip({
    required this.filter,
    required this.isActive,
    required this.onTap,
  });

  String get _label {
    switch (filter) {
      case StockLedgerPoolFilter.all:
        return AppStrings.STOCK_LEDGER_POOL_ALL;
      case StockLedgerPoolFilter.bags:
        return AppStrings.STOCK_LEDGER_POOL_BAGS;
      case StockLedgerPoolFilter.loose:
        return AppStrings.STOCK_LEDGER_POOL_LOOSE;
      case StockLedgerPoolFilter.raw:
        return AppStrings.STOCK_LEDGER_POOL_RAW;
      case StockLedgerPoolFilter.packing:
        return AppStrings.STOCK_LEDGER_POOL_PACKING;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isActive ? AppColors.SURFACE : Colors.transparent,
      borderRadius: BorderRadius.circular(AppRadius.sm),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.sm),
        onTap: onTap,
        child: Container(
          height: 26,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
          alignment: Alignment.center,
          child: Text(
            _label,
            style: AppTypography.bodySmall.copyWith(
              fontSize: 12.5,
              fontWeight: FontWeight.w500,
              color: isActive ? AppColors.TEXT_PRIMARY : AppColors.TEXT_SECONDARY,
            ),
          ),
        ),
      ),
    );
  }
}

class _FamilyChip extends StatelessWidget {
  final StockLedgerFamily family;
  final bool isActive;
  final VoidCallback onTap;

  const _FamilyChip({
    required this.family,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final meta = StockLedgerMeta.families[family]!;
    return Material(
      color: isActive ? AppColors.SURFACE : Colors.transparent,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: isActive ? AppColors.BORDER : AppColors.HAIRLINE,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: meta.color.withValues(alpha: isActive ? 1 : 0.3),
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                meta.label,
                style: AppTypography.bodySmall.copyWith(
                  fontSize: 12.5,
                  color: isActive ? AppColors.TEXT_PRIMARY : const Color(0xFF6B756F),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FollowingBar extends StatelessWidget {
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _FollowingBar({required this.state, required this.cubit});

  @override
  Widget build(BuildContext context) {
    final List<int> indexes = cubit.indexesForSource(state.highlightedSourceId!);
    final StockLedgerRow? first = indexes.isEmpty ? null : state.rows[indexes.first];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xl, vertical: AppSpacing.sm),
      decoration: const BoxDecoration(
        color: Color(0xFFEBF5F5),
        border: Border(bottom: BorderSide(color: Color(0xFFC9E0E0))),
      ),
      child: Row(
        children: [
          const Icon(Icons.alt_route_rounded, size: 16, color: Color(0xFF337E82)),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text.rich(
              TextSpan(
                style: AppTypography.bodySmall.copyWith(fontSize: 12.5, color: AppColors.TEXT_PRIMARY),
                children: [
                  TextSpan(text: '${AppStrings.STOCK_LEDGER_FOLLOWING} '),
                  TextSpan(
                    text: state.highlightedSourceId,
                    style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w600),
                  ),
                  TextSpan(
                    text: ' · ${first?.source?.label ?? ''} — ${indexes.length} '
                        '${AppStrings.STOCK_LEDGER_LINKED_EVENTS_HIGHLIGHTED}',
                  ),
                ],
              ),
            ),
          ),
          TextButton.icon(
            onPressed: cubit.clearSourceHighlight,
            icon: const Icon(Icons.close_rounded, size: 14),
            label: Text(
              AppStrings.STOCK_LEDGER_CLEAR,
              style: AppTypography.bodySmall.copyWith(fontSize: 12),
            ),
            style: TextButton.styleFrom(
              foregroundColor: AppColors.TEXT_PRIMARY,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              minimumSize: const Size(0, 24),
            ),
          ),
        ],
      ),
    );
  }
}

class _ChainBody extends StatefulWidget {
  final StockLedgerState state;
  final StockLedgerCubit cubit;

  const _ChainBody({required this.state, required this.cubit});

  @override
  State<_ChainBody> createState() => _ChainBodyState();
}

class _ChainBodyState extends State<_ChainBody> {
  final Map<int, GlobalKey> _nodeKeys = {};
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    WidgetsBinding.instance.addPostFrameCallback((_) => _onScroll());
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  @override
  void didUpdateWidget(_ChainBody oldWidget) {
    super.didUpdateWidget(oldWidget);
    final int? selected = widget.state.selectedIndex;
    if (selected != null && selected != oldWidget.state.selectedIndex) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToNode(selected));
    }
    if (widget.state.rows != oldWidget.state.rows ||
        widget.state.poolFilter != oldWidget.state.poolFilter ||
        widget.state.enabledFamilies != oldWidget.state.enabledFamilies) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _onScroll());
    }
  }

  void _scrollToNode(int index) {
    final GlobalKey? key = _nodeKeys[index];
    final BuildContext? nodeContext = key?.currentContext;
    if (nodeContext == null) return;
    Scrollable.ensureVisible(
      nodeContext,
      alignment: 0.1,
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
    );
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final ScrollPosition position = _scrollController.position;
    final double contentExtent = position.maxScrollExtent + position.viewportDimension;
    if (contentExtent <= 0) return;

    final double top = (position.pixels / contentExtent * 100).clamp(0, 100);
    final double bottom =
        ((position.pixels + position.viewportDimension) / contentExtent * 100)
            .clamp(0, 100);
    widget.cubit.viewportRange.value = StockLedgerViewportRange(
      top: top,
      height: (bottom - top).clamp(0, 100),
    );
  }

  @override
  Widget build(BuildContext context) {
    final StockLedgerState state = widget.state;
    final StockLedgerCubit cubit = widget.cubit;

    if (state.status == StockLedgerStatus.loading) {
      return _LoadingSkeleton(key: const ValueKey('loading'), state: state);
    }
    if (!state.isReady) {
      return _EmptyIllustration(key: const ValueKey('empty'), state: state);
    }
    if (state.rows.isEmpty) {
      return _EmptyIllustration(key: const ValueKey('empty'), state: state);
    }

    final bool onlyBookends = state.rows.length == 2 &&
        state.rows.first.isOpening &&
        state.rows.last.isClosing;
    if (onlyBookends) {
      return _NoEventsView(
        key: const ValueKey('bookends'),
        opening: state.rows.first,
        closing: state.rows.last,
      );
    }

    final StockLedgerChainBuilder builder = StockLedgerChainBuilder(
      rows: state.rows,
      poolFilter: state.poolFilter,
      enabledFamilies: state.enabledFamilies,
      selectedIndex: state.selectedIndex,
      highlightedSourceId: state.highlightedSourceId,
    );
    final List<StockLedgerChainNode> nodes = builder.build();
    final Map<int, int> hiddenBefore = StockLedgerChainBuilder.hiddenCountsBefore(nodes);

    return SingleChildScrollView(
      key: const ValueKey('chain'),
      controller: _scrollController,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 32, 80),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 840),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: _buildRows(nodes, hiddenBefore, cubit, state),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildRows(
    List<StockLedgerChainNode> nodes,
    Map<int, int> hiddenBefore,
    StockLedgerCubit cubit,
    StockLedgerState state,
  ) {
    final List<Widget> widgets = [];
    DateTime? lastDay;
    StockLedgerChainNode? prevVisible;
    final Set<int> liveIndexes = {};

    for (final node in nodes) {
      if (!node.isVisible) continue;
      liveIndexes.add(node.index);

      final DateTime? t = node.row.occurredAtTime?.toUtc();
      final DateTime? day = t == null ? null : DateTime.utc(t.year, t.month, t.day);
      if (day != null && day != lastDay) {
        widgets.add(_DayDivider(day: day));
        lastDay = day;
      }

      final int hidden = hiddenBefore[node.index] ?? 0;
      if (hidden > 0) {
        widgets.add(
          _HiddenStub(
            count: hidden,
            poolFilter: state.poolFilter,
            onShow: cubit.showEverything,
          ),
        );
      }

      if (prevVisible != null) {
        widgets.add(_LinkSegment(from: prevVisible, to: node));
      }

      final GlobalKey nodeKey = _nodeKeys.putIfAbsent(node.index, () => GlobalKey());
      widgets.add(
        KeyedSubtree(
          key: nodeKey,
          child: _NodeCard(node: node, cubit: cubit, state: state),
        ),
      );
      prevVisible = node;
    }

    _nodeKeys.removeWhere((index, _) => !liveIndexes.contains(index));
    return widgets;
  }
}

class _DayDivider extends StatelessWidget {
  final DateTime day;

  const _DayDivider({required this.day});

  static final DateFormat _fmt = DateFormat('EEE d MMM yyyy');

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 50,
      child: Row(
        children: [
          Container(
            margin: const EdgeInsets.only(left: 4),
            height: 26,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
            decoration: BoxDecoration(
              color: AppColors.TEXT_PRIMARY,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.today_rounded, size: 14, color: AppColors.TEXT_ON_PRIMARY),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  _fmt.format(day),
                  style: const TextStyle(
                    color: AppColors.TEXT_ON_PRIMARY,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.smd),
          const Expanded(child: Divider(height: 1, color: AppColors.BORDER)),
        ],
      ),
    );
  }
}

class _HiddenStub extends StatelessWidget {
  final int count;
  final StockLedgerPoolFilter poolFilter;
  final VoidCallback onShow;

  const _HiddenStub({
    required this.count,
    required this.poolFilter,
    required this.onShow,
  });

  @override
  Widget build(BuildContext context) {
    final String suffix = poolFilter == StockLedgerPoolFilter.all
        ? AppStrings.STOCK_LEDGER_FILTERED_OUT
        : '${AppStrings.STOCK_LEDGER_DIDNT_TOUCH_PREFIX} ${_poolLabel(poolFilter)}';
    return SizedBox(
      height: 34,
      child: Row(
        children: [
          SizedBox(
            width: 76,
            child: Center(
              child: Container(width: 0, height: 34, decoration: const BoxDecoration(
                border: Border(left: BorderSide(color: AppColors.BORDER_STRONG, width: 2)),
              )),
            ),
          ),
          OutlinedButton(
            onPressed: onShow,
            style: OutlinedButton.styleFrom(
              minimumSize: const Size(0, 24),
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
              side: const BorderSide(color: AppColors.BORDER_STRONG),
              foregroundColor: AppColors.TEXT_SECONDARY,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
            ),
            child: Text(
              '$count ${AppStrings.STOCK_LEDGER_OTHER_EVENTS_SUFFIX} · $suffix — '
              '${AppStrings.STOCK_LEDGER_SHOW}',
              style: AppTypography.bodySmall.copyWith(fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  static String _poolLabel(StockLedgerPoolFilter f) {
    switch (f) {
      case StockLedgerPoolFilter.bags:
        return AppStrings.STOCK_LEDGER_POOL_BAGS;
      case StockLedgerPoolFilter.loose:
        return AppStrings.STOCK_LEDGER_POOL_LOOSE;
      case StockLedgerPoolFilter.raw:
        return AppStrings.STOCK_LEDGER_POOL_RAW;
      case StockLedgerPoolFilter.packing:
        return AppStrings.STOCK_LEDGER_POOL_PACKING;
      case StockLedgerPoolFilter.all:
        return '';
    }
  }
}

class _LinkSegment extends StatelessWidget {
  final StockLedgerChainNode from;
  final StockLedgerChainNode to;

  const _LinkSegment({required this.from, required this.to});

  @override
  Widget build(BuildContext context) {
    final Color color = StockLedgerLinkStyle.solidColorFor(from.netDirection);
    final double opacity = from.isDimmed || to.isDimmed ? 0.35 : 1;

    return Opacity(
      opacity: opacity,
      child: SizedBox(
        height: 46,
        child: Row(
          children: [
            SizedBox(
              width: 76,
              child: Center(child: Container(width: 3, height: 46, color: color)),
            ),
          ],
        ),
      ),
    );
  }
}

class _NodeCard extends StatelessWidget {
  final StockLedgerChainNode node;
  final StockLedgerCubit cubit;
  final StockLedgerState state;

  const _NodeCard({required this.node, required this.cubit, required this.state});

  @override
  Widget build(BuildContext context) {
    final meta = StockLedgerMeta.families[node.meta.family]!;
    final bool isExpanded = state.expandedIndexes.contains(node.index);

    return Opacity(
      opacity: node.isDimmed ? 0.3 : 1,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 76,
            child: Align(
              alignment: Alignment.topCenter,
              child: Container(
                width: node.isBalance ? 40 : 30,
                height: node.isBalance ? 40 : 30,
                decoration: BoxDecoration(
                  color: node.isBalance ? meta.tint : meta.color,
                  shape: BoxShape.circle,
                  border: node.isBalance
                      ? null
                      : Border.all(color: AppColors.SURFACE, width: 3),
                  boxShadow: node.isSelected
                      ? [
                          BoxShadow(
                            color: AppColors.PRIMARY.withValues(alpha: 0.4),
                            spreadRadius: 3,
                          ),
                        ]
                      : null,
                ),
                alignment: Alignment.center,
                child: Icon(
                  node.meta.variant == 'revert' ? Icons.undo_rounded : meta.icon,
                  size: node.isBalance ? 20 : 16,
                  color: node.isBalance ? AppColors.PRIMARY : AppColors.TEXT_ON_PRIMARY,
                ),
              ),
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 20),
              child: node.isBalance
                  ? _BalanceCard(node: node, cubit: cubit)
                  : _EventCard(
                      node: node,
                      cubit: cubit,
                      isExpanded: isExpanded,
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  final StockLedgerChainNode node;
  final StockLedgerCubit cubit;

  const _BalanceCard({required this.node, required this.cubit});

  @override
  Widget build(BuildContext context) {
    final StockLedgerRow row = node.row;
    final bool isHead = row.isOpening;
    final String tag = isHead ? AppStrings.STOCK_LEDGER_HEAD : AppStrings.STOCK_LEDGER_TAIL;
    final String summary = isHead
        ? AppStrings.STOCK_LEDGER_STARTING_STATE
        : AppStrings.STOCK_LEDGER_ENDING_STATE;

    return Material(
      color: AppColors.SURFACE,
      borderRadius: BorderRadius.circular(AppRadius.xl),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.xl),
        onTap: () => cubit.selectNode(node.index),
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.xl),
            border: Border.all(
              color: node.isSelected ? AppColors.PRIMARY : AppColors.BORDER,
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(node.meta.title, style: AppTypography.titleMedium.copyWith(fontSize: 16)),
                  const SizedBox(width: AppSpacing.sm),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.PRIMARY,
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: Text(
                      tag,
                      style: const TextStyle(
                        color: AppColors.TEXT_ON_PRIMARY,
                        fontFamily: 'monospace',
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 2),
              Text(
                '${DateFormatter.instantLabel(row.occurredAtTime)} · $summary',
                style: AppTypography.bodySmall.copyWith(fontSize: 12.5),
              ),
              const SizedBox(height: AppSpacing.smd),
              _FullStateGrid(row: row),
            ],
          ),
        ),
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  final StockLedgerChainNode node;
  final StockLedgerCubit cubit;
  final bool isExpanded;

  const _EventCard({
    required this.node,
    required this.cubit,
    required this.isExpanded,
  });

  @override
  Widget build(BuildContext context) {
    final StockLedgerRow row = node.row;
    final meta = StockLedgerMeta.families[node.meta.family]!;
    final String detailLabel = StockLedgerMeta.detailLabel(row.detail);

    return Material(
      color: AppColors.SURFACE,
      borderRadius: BorderRadius.circular(AppRadius.lg),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.lg),
        onTap: () => cubit.selectNode(node.index),
        child: Container(
          padding: const EdgeInsets.fromLTRB(16, 13, 16, 12),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border: Border.all(
              color: node.isSelected
                  ? AppColors.PRIMARY
                  : (node.isNegative
                      ? const Color(0xFFDCA796)
                      : AppColors.BORDER),
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    decoration: BoxDecoration(
                      color: meta.tint,
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    alignment: Alignment.center,
                    child: Icon(
                      node.meta.variant == 'revert' ? Icons.undo_rounded : meta.icon,
                      size: 18,
                      color: meta.color,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: AppSpacing.sm,
                      children: [
                        Text(
                          node.meta.title,
                          style: AppTypography.labelMedium.copyWith(fontSize: 14),
                        ),
                        if (detailLabel.isNotEmpty)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: meta.tint,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              detailLabel,
                              style: TextStyle(
                                color: meta.color,
                                fontSize: 12,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                          ),
                        if (node.isNegative)
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: const Color(0xFFF7E3DD),
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                const Icon(Icons.warning_amber_rounded, size: 14, color: Color(0xFFAC3A1F)),
                                const SizedBox(width: 4),
                                Text(
                                  '${AppStrings.STOCK_LEDGER_BELOW_ZERO_PREFIX} ${_negativePools(row)}',
                                  style: const TextStyle(
                                    color: Color(0xFFAC3A1F),
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
                  Text(
                    row.occurredAtTime == null
                        ? ''
                        : DateFormat('HH:mm').format(row.occurredAtTime!.toUtc().add(const Duration(hours: 5, minutes: 30))),
                    style: AppTypography.bodySmall.copyWith(
                      fontSize: 12,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
              Padding(
                padding: const EdgeInsets.only(left: 40, top: AppSpacing.sm),
                child: Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: AppSpacing.sm,
                  runSpacing: AppSpacing.xs,
                  children: [
                    if (row.source != null) _SourceChip(row: row, cubit: cubit),
                    Text(
                      row.actor == null
                          ? '${AppStrings.STOCK_LEDGER_BY_PREFIX} ${AppStrings.STOCK_LEDGER_SYSTEM_ACTOR}'
                          : '${AppStrings.STOCK_LEDGER_BY_PREFIX} ${row.actor!.name}',
                      style: AppTypography.bodySmall.copyWith(fontSize: 12),
                    ),
                  ],
                ),
              ),
              if (_changedGroups(row).isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(left: 40, top: AppSpacing.smd),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: _changedGroups(row),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.only(left: 40, top: AppSpacing.smd),
                child: Container(
                  padding: const EdgeInsets.only(top: 9),
                  decoration: const BoxDecoration(
                    border: Border(top: BorderSide(color: AppColors.HAIRLINE)),
                  ),
                  child: Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: AppSpacing.md,
                    runSpacing: AppSpacing.xs,
                    children: [
                      Text(
                        AppStrings.STOCK_LEDGER_AVAILABLE_AFTER,
                        style: AppTypography.labelSmall.copyWith(fontSize: 11),
                      ),
                      ..._availableSnapshot(row),
                      TextButton.icon(
                        onPressed: () => cubit.toggleExpanded(node.index),
                        icon: Icon(
                          isExpanded ? Icons.expand_less_rounded : Icons.expand_more_rounded,
                          size: 16,
                        ),
                        label: Text(
                          isExpanded
                              ? AppStrings.STOCK_LEDGER_HIDE_FULL_STATE
                              : AppStrings.STOCK_LEDGER_FULL_STATE,
                          style: AppTypography.bodySmall.copyWith(
                            fontSize: 12,
                            color: AppColors.PRIMARY,
                          ),
                        ),
                        style: TextButton.styleFrom(
                          foregroundColor: AppColors.PRIMARY,
                          minimumSize: const Size(0, 24),
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (isExpanded)
                Padding(
                  padding: const EdgeInsets.only(left: 40, top: AppSpacing.sm),
                  child: _FullStateGrid(row: row),
                ),
            ],
          ),
        ),
      ),
    );
  }

  static String _negativePools(StockLedgerRow row) {
    final List<String> names = [];
    for (final p in row.bagPools) {
      if (p.figures.available < 0) {
        names.add('${AppStrings.STOCK_LEDGER_POOL_NAME_BAGS} ${p.packaging.packetWeight} kg');
      }
    }
    for (final p in row.packetPools) {
      if (p.figures.available < 0) {
        names.add('${AppStrings.STOCK_LEDGER_POOL_NAME_LOOSE} ${p.packetWeight} kg');
      }
    }
    if (row.rawMaterial.figures.availableValue < 0) {
      names.add(AppStrings.STOCK_LEDGER_POOL_NAME_RAW);
    }
    for (final m in row.otherMaterials) {
      if (m.figures.availableValue < 0) names.add(m.materialType.name);
    }
    return names.join(', ');
  }

  static List<Widget> _changedGroups(StockLedgerRow row) {
    final List<Widget> widgets = [];

    final List<LedgerBagPool> bagChanges = row.bagPools.where((p) => !p.change.isZero).toList();
    if (bagChanges.isNotEmpty) {
      widgets.add(_GroupRow(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_BAGS,
        pairs: [
          for (final p in bagChanges)
            if (p.change.onHand != 0)
              _Pair(label: AppStrings.STOCK_LEDGER_FIELD_ON_HAND, from: p.figures.onHand - p.change.onHand, to: p.figures.onHand, delta: p.change.onHand)
            else if (p.change.reserved != 0)
              _Pair(label: AppStrings.STOCK_LEDGER_FIELD_RESERVED, from: p.figures.reserved - p.change.reserved, to: p.figures.reserved, delta: p.change.reserved)
            else if (p.change.consumed != 0)
              _Pair(label: AppStrings.STOCK_LEDGER_FIELD_CONSUMED, from: p.figures.consumed - p.change.consumed, to: p.figures.consumed, delta: p.change.consumed)
            else
              _Pair(label: AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, from: p.figures.available - p.change.available, to: p.figures.available, delta: p.change.available),
        ],
      ));
    }

    final List<LedgerPacketPool> looseChanges = row.packetPools.where((p) => !p.change.isZero).toList();
    if (looseChanges.isNotEmpty) {
      widgets.add(_GroupRow(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_LOOSE,
        pairs: [
          for (final p in looseChanges)
            _Pair(label: AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, from: p.figures.available - p.change.available, to: p.figures.available, delta: p.change.available),
        ],
      ));
    }

    if (!row.rawMaterial.change.isZero) {
      final r = row.rawMaterial;
      widgets.add(_GroupRow(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_RAW,
        pairs: [
          _Pair(
            label: AppStrings.STOCK_LEDGER_FIELD_AVAILABLE,
            from: r.figures.availableValue - r.change.availableValue,
            to: r.figures.availableValue,
            delta: r.change.availableValue,
          ),
        ],
      ));
    }

    for (final m in row.otherMaterials) {
      if (m.change.isZero) continue;
      widgets.add(_GroupRow(
        name: m.materialType.name,
        pairs: [
          _Pair(
            label: AppStrings.STOCK_LEDGER_FIELD_AVAILABLE,
            from: m.figures.availableValue - m.change.availableValue,
            to: m.figures.availableValue,
            delta: m.change.availableValue,
          ),
        ],
      ));
    }

    return widgets;
  }

  static List<Widget> _availableSnapshot(StockLedgerRow row) {
    final List<Widget> chips = [];
    if (row.bagPools.isNotEmpty) {
      chips.add(_SnapChip(
        label: AppStrings.STOCK_LEDGER_POOL_BAGS,
        value: row.bagPools.map((p) => _fmt(p.figures.available)).join(' · '),
        negative: row.bagPools.any((p) => p.figures.available < 0),
      ));
    }
    if (row.packetPools.isNotEmpty) {
      chips.add(_SnapChip(
        label: AppStrings.STOCK_LEDGER_POOL_LOOSE,
        value: row.packetPools.map((p) => _fmt(p.figures.available)).join(' · '),
        negative: row.packetPools.any((p) => p.figures.available < 0),
      ));
    }
    chips.add(_SnapChip(
      label: AppStrings.STOCK_LEDGER_POOL_NAME_RAW,
      value: '${_fmt(row.rawMaterial.figures.availableValue)} kg',
      negative: row.rawMaterial.figures.availableValue < 0,
    ));
    for (final m in row.otherMaterials) {
      chips.add(_SnapChip(
        label: m.materialType.name,
        value: _fmt(m.figures.availableValue),
        negative: m.figures.availableValue < 0,
      ));
    }
    return chips;
  }
}

class _Pair {
  final String label;
  final num from;
  final num to;
  final num delta;

  const _Pair({required this.label, required this.from, required this.to, required this.delta});
}

class _GroupRow extends StatelessWidget {
  final String name;
  final List<_Pair> pairs;

  const _GroupRow({required this.name, required this.pairs});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Wrap(
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              name,
              style: AppTypography.labelSmall.copyWith(fontSize: 11, letterSpacing: 0.3),
            ),
          ),
          for (final p in pairs)
            Padding(
              padding: const EdgeInsets.only(right: AppSpacing.md, bottom: 2),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(p.label, style: AppTypography.bodySmall.copyWith(fontSize: 12)),
                  const SizedBox(width: 4),
                  Text(
                    '${_fmt(p.from)} → ${_fmt(p.to)}',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: p.to < 0 ? const Color(0xFFAC3A1F) : AppColors.TEXT_PRIMARY,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: p.delta > 0
                          ? const Color(0xFFE3F3E6)
                          : (p.delta < 0 ? const Color(0xFFF7E3DD) : AppColors.SURFACE_VARIANT),
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: Text(
                      _signed(p.delta),
                      style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: FontWeight.w600,
                        color: p.delta > 0
                            ? const Color(0xFF237A39)
                            : (p.delta < 0 ? const Color(0xFFAC3A1F) : AppColors.TEXT_SECONDARY),
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

class _SnapChip extends StatelessWidget {
  final String label;
  final String value;
  final bool negative;

  const _SnapChip({required this.label, required this.value, required this.negative});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
      decoration: BoxDecoration(
        color: negative ? const Color(0xFFF7E3DD) : Colors.transparent,
        borderRadius: BorderRadius.circular(5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: AppTypography.bodySmall.copyWith(fontSize: 12)),
          const SizedBox(width: 5),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: negative ? const Color(0xFFAC3A1F) : AppColors.TEXT_PRIMARY,
            ),
          ),
        ],
      ),
    );
  }
}

class _SourceChip extends StatelessWidget {
  final StockLedgerRow row;
  final StockLedgerCubit cubit;

  const _SourceChip({required this.row, required this.cubit});

  @override
  Widget build(BuildContext context) {
    final source = row.source!;
    final (label, icon) = StockLedgerMeta.sourceKindMeta(source.kind);
    final List<String> parts = source.publicId.split('-');
    final String shortId = parts.length > 1
        ? '${parts[0]}-${parts[1].substring(0, parts[1].length > 4 ? 4 : parts[1].length)}'
        : source.publicId;

    return OutlinedButton(
      onPressed: () => cubit.toggleSourceHighlight(source.publicId),
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(0, 26),
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
        side: const BorderSide(color: AppColors.BORDER),
        foregroundColor: AppColors.TEXT_PRIMARY,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(AppRadius.sm)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppColors.TEXT_SECONDARY),
          const SizedBox(width: AppSpacing.xs),
          Text(
            shortId,
            style: const TextStyle(fontFamily: 'monospace', fontWeight: FontWeight.w500, fontSize: 12),
          ),
          const SizedBox(width: 4),
          Text('·', style: AppTypography.bodySmall.copyWith(fontSize: 12)),
          const SizedBox(width: 4),
          Text(label, style: AppTypography.bodySmall.copyWith(fontSize: 12)),
        ],
      ),
    );
  }
}

class _FullStateGrid extends StatelessWidget {
  final StockLedgerRow row;

  const _FullStateGrid({required this.row});

  @override
  Widget build(BuildContext context) {
    final List<Widget> blocks = [];

    for (final p in row.bagPools) {
      blocks.add(_PoolBlock(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_BAGS,
        sub: '${p.packaging.packetWeight} kg × ${p.packaging.packets}',
        rows: [
          (AppStrings.STOCK_LEDGER_FIELD_ON_HAND, p.figures.onHand, p.change.onHand != 0),
          (AppStrings.STOCK_LEDGER_FIELD_RESERVED, p.figures.reserved, p.change.reserved != 0),
          (AppStrings.STOCK_LEDGER_FIELD_CONSUMED, p.figures.consumed, p.change.consumed != 0),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, p.figures.available, p.change.available != 0),
        ],
      ));
    }
    for (final p in row.packetPools) {
      blocks.add(_PoolBlock(
        name: AppStrings.STOCK_LEDGER_POOL_NAME_LOOSE,
        sub: '${p.packetWeight} kg',
        rows: [
          (AppStrings.STOCK_LEDGER_FIELD_ON_HAND, p.figures.onHand, p.change.onHand != 0),
          (AppStrings.STOCK_LEDGER_FIELD_RESERVED, p.figures.reserved, p.change.reserved != 0),
          (AppStrings.STOCK_LEDGER_FIELD_CONSUMED, p.figures.consumed, p.change.consumed != 0),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, p.figures.available, p.change.available != 0),
        ],
      ));
    }
    final r = row.rawMaterial;
    blocks.add(_PoolBlock(
      name: AppStrings.STOCK_LEDGER_POOL_NAME_RAW,
      sub: 'kg',
      rows: [
        (AppStrings.STOCK_LEDGER_FIELD_INCOMING, r.figures.incomingValue, r.change.incomingValue != 0),
        (AppStrings.STOCK_LEDGER_FIELD_PACKED, r.figures.packedValue, r.change.packedValue != 0),
        (AppStrings.STOCK_LEDGER_FIELD_REJECTED, r.figures.rejectedValue, r.change.rejectedValue != 0),
        (AppStrings.STOCK_LEDGER_FIELD_WASTED, r.figures.wastedValue, r.change.wastedValue != 0),
        (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, r.figures.availableValue, r.change.availableValue != 0),
      ],
    ));
    for (final m in row.otherMaterials) {
      blocks.add(_PoolBlock(
        name: m.materialType.name,
        sub: m.materialType.unitType,
        rows: [
          (AppStrings.STOCK_LEDGER_FIELD_INCOMING, m.figures.incomingValue, m.change.incomingValue != 0),
          (AppStrings.STOCK_LEDGER_FIELD_PACKED, m.figures.packedValue, m.change.packedValue != 0),
          (AppStrings.STOCK_LEDGER_FIELD_AVAILABLE, m.figures.availableValue, m.change.availableValue != 0),
        ],
      ));
    }

    const int crossAxisCount = 3;
    final List<Widget> lines = [];
    for (int i = 0; i < blocks.length; i += crossAxisCount) {
      lines.add(
        Padding(
          padding: EdgeInsets.only(top: i > 0 ? AppSpacing.xs : 0),
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (int c = 0; c < crossAxisCount; c++) ...[
                  if (c > 0) const SizedBox(width: AppSpacing.xs),
                  Expanded(
                    child: i + c < blocks.length
                        ? blocks[i + c]
                        : const SizedBox.shrink(),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: lines,
    );
  }
}

class _PoolBlock extends StatelessWidget {
  final String name;
  final String sub;
  final List<(String, num, bool)> rows;

  const _PoolBlock({required this.name, required this.sub, required this.rows});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: const Color(0xFFF6F8F7),
        border: Border.all(color: AppColors.HAIRLINE),
        borderRadius: BorderRadius.circular(AppRadius.sm),
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
                  style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: AppColors.TEXT_PRIMARY),
                ),
                TextSpan(
                  text: ' $sub',
                  style: AppTypography.bodySmall.copyWith(fontSize: 11),
                ),
              ],
            ),
          ),
          const SizedBox(height: 2),
          for (final (label, value, changed) in rows)
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(label, style: AppTypography.bodySmall.copyWith(fontSize: 11.5)),
                Text(
                  _fmt(value),
                  style: TextStyle(
                    fontSize: 11.5,
                    fontWeight: changed ? FontWeight.w600 : FontWeight.w400,
                    color: value < 0
                        ? const Color(0xFFAC3A1F)
                        : (changed ? AppColors.PRIMARY : AppColors.TEXT_PRIMARY),
                  ),
                ),
              ],
            ),
        ],
      ),
    );
  }
}

class _LoadingSkeleton extends StatelessWidget {
  final StockLedgerState state;

  const _LoadingSkeleton({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 24, 32, 40),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 840),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final opacity in const [1.0, 0.8, 0.6, 0.4, 0.25])
                Opacity(
                  opacity: opacity,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Row(
                      children: [
                        const SizedBox(width: 76),
                        Expanded(
                          child: Container(
                            height: 70,
                            decoration: BoxDecoration(
                              color: AppColors.SURFACE,
                              border: Border.all(color: AppColors.HAIRLINE),
                              borderRadius: BorderRadius.circular(AppRadius.lg),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.only(left: 76),
                child: Row(
                  children: [
                    const Icon(Icons.hourglass_top_rounded, size: 16, color: AppColors.TEXT_SECONDARY),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Text(
                        '${AppStrings.STOCK_LEDGER_BUILDING_PREFIX} ${state.productName ?? ''}…',
                        style: AppTypography.bodySmall.copyWith(fontSize: 12.5),
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

class _NoEventsView extends StatelessWidget {
  final StockLedgerRow opening;
  final StockLedgerRow closing;

  const _NoEventsView({super.key, required this.opening, required this.closing});

  @override
  Widget build(BuildContext context) {
    final bool identical = opening.bagPools.length == closing.bagPools.length;

    return SingleChildScrollView(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 24, 32, 40),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 840),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _BookendRow(
                title: AppStrings.STOCK_LEDGER_OPENING_BALANCE,
                subtitle: DateFormatter.instantLabel(opening.occurredAtTime),
              ),
              SizedBox(
                height: 90,
                child: Row(
                  children: [
                    const SizedBox(width: 76),
                    const Icon(Icons.horizontal_rule_rounded, size: 18, color: AppColors.TEXT_SECONDARY),
                    const SizedBox(width: AppSpacing.sm),
                    Expanded(
                      child: Text(
                        AppStrings.STOCK_LEDGER_NO_EVENTS_NOTE,
                        style: AppTypography.bodyMedium.copyWith(fontSize: 13, color: AppColors.TEXT_SECONDARY),
                      ),
                    ),
                  ],
                ),
              ),
              _BookendRow(
                title: AppStrings.STOCK_LEDGER_CLOSING_BALANCE,
                subtitle:
                    '${DateFormatter.instantLabel(closing.occurredAtTime)} '
                    '${identical ? AppStrings.STOCK_LEDGER_IDENTICAL_TO_OPENING : ''}',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BookendRow extends StatelessWidget {
  final String title;
  final String subtitle;

  const _BookendRow({required this.title, required this.subtitle});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 76,
          child: Center(
            child: Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: AppColors.PRIMARY,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.SURFACE, width: 3),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.flag_outlined, size: 16, color: AppColors.TEXT_ON_PRIMARY),
            ),
          ),
        ),
        Expanded(
          child: Container(
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
            decoration: BoxDecoration(
              color: AppColors.SURFACE,
              border: Border.all(color: AppColors.BORDER, width: 1.5),
              borderRadius: BorderRadius.circular(AppRadius.xl),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(title, style: AppTypography.titleMedium.copyWith(fontSize: 16)),
                const SizedBox(height: 2),
                Text(subtitle, style: AppTypography.bodySmall.copyWith(fontSize: 12.5)),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _EmptyIllustration extends StatelessWidget {
  final StockLedgerState state;

  const _EmptyIllustration({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final bool isNotStarted = state.status == StockLedgerStatus.notStarted;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            _DashedFlag(label: AppStrings.STOCK_LEDGER_HEAD),
            Container(
              width: 0,
              height: 150,
              margin: const EdgeInsets.only(right: 52),
              decoration: const BoxDecoration(
                border: Border(left: BorderSide(color: AppColors.BORDER_STRONG, width: 2)),
              ),
            ),
            _DashedFlag(label: AppStrings.STOCK_LEDGER_TAIL),
            const SizedBox(height: AppSpacing.lg),
            Text(
              isNotStarted
                  ? AppStrings.STOCK_LEDGER_NOT_STARTED_TITLE
                  : AppStrings.STOCK_LEDGER_EMPTY_TITLE,
              style: AppTypography.titleMedium.copyWith(fontSize: 16),
            ),
            const SizedBox(height: AppSpacing.xs),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Text(
                isNotStarted
                    ? AppStrings.STOCK_LEDGER_NOT_STARTED_BODY
                    : AppStrings.STOCK_LEDGER_EMPTY_BODY,
                textAlign: TextAlign.center,
                style: AppTypography.bodyMedium.copyWith(
                  fontSize: 13.5,
                  color: AppColors.TEXT_SECONDARY,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DashedFlag extends StatelessWidget {
  final String label;

  const _DashedFlag({required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(color: AppColors.BORDER_STRONG, width: 2),
          ),
          alignment: Alignment.center,
          child: const Icon(Icons.flag_outlined, size: 18, color: AppColors.TEXT_SECONDARY),
        ),
        const SizedBox(width: AppSpacing.smd),
        SizedBox(
          width: 40,
          child: Text(
            label,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 11,
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ),
      ],
    );
  }
}
