import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/return_order_model.dart';
import '../../data/models/return_order_status.dart';
import 'return_order_status_badge.dart';

/// The returns queue.
///
/// Every row carries its own verbs, because a return's available actions depend
/// on where it sits in the lifecycle rather than on anything about the page it
/// is displayed on.
class ReturnOrdersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'return_orders';
  static const String COLUMN_RETURN_ID = 'return_id';
  static const String COLUMN_CLIENT = 'client';
  static const String COLUMN_ORDER = 'order';
  static const String COLUMN_STATUS = 'status';
  static const String COLUMN_RETURN_DATE = 'return_date';
  static const String COLUMN_RAISED_BY = 'raised_by';
  static const String COLUMN_ACTIONS = 'return_actions';

  final List<ReturnOrderModel> returnOrders;
  final bool isLoading;
  final bool isMutating;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final void Function(ReturnOrderModel returnOrder)? onView;
  final void Function(ReturnOrderModel returnOrder)? onEdit;
  final void Function(ReturnOrderModel returnOrder)? onAccept;
  final void Function(ReturnOrderModel returnOrder)? onReject;
  final void Function(ReturnOrderModel returnOrder)? onUnreject;
  final void Function(ReturnOrderModel returnOrder)? onRevertAccept;
  final void Function(ReturnOrderModel returnOrder)? onViewSlip;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final Widget? searchBarTrailing;

  const ReturnOrdersTable({
    super.key,
    required this.returnOrders,
    required this.isLoading,
    required this.isMutating,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.onView,
    this.onEdit,
    this.onAccept,
    this.onReject,
    this.onUnreject,
    this.onRevertAccept,
    this.onViewSlip,
    this.hasMore = false,
    this.onLoadMore,
    this.searchBarActions = const [],
    this.searchBarTrailing,
  });

  @override
  State<ReturnOrdersTable> createState() => ReturnOrdersTableState();
}

class ReturnOrdersTableState extends State<ReturnOrdersTable> {
  final GlobalKey<AppDataTableState<ReturnOrderModel>> _tableKey =
      GlobalKey<AppDataTableState<ReturnOrderModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  List<AppDataColumn> get _columns => const [
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_RETURN_ID,
      label: AppStrings.COLUMN_RETURN_ID,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_CLIENT,
      label: AppStrings.COLUMN_RETURN_CLIENT,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_ORDER,
      label: AppStrings.COLUMN_RETURN_ORDER,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_RETURN_STATUS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_RETURN_DATE,
      label: AppStrings.COLUMN_RETURN_DATE,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_RAISED_BY,
      label: AppStrings.COLUMN_RETURN_RAISED_BY,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: ReturnOrdersTable.COLUMN_ACTIONS,
      label: AppStrings.COLUMN_RETURN_ACTIONS,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
  ];

  List<String> get _filterOptions => widget.availableFilters
      .where((filter) => filter.kind != ClientFilterKind.unsupported)
      .map((filter) => filter.key)
      .toList();

  List<String> get _sortOptions =>
      widget.availableSorts.map((sort) => sort.key).toList();

  ClientFilterModel? _filterFor(String key) {
    for (final filter in widget.availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  List<FilterValueOption> _valueOptionsFor(String key) {
    final ClientFilterModel? filter = _filterFor(key);
    if (filter == null || !filter.isSelect) return const [];

    return filter.options
        .map(
          (option) =>
              FilterValueOption(value: option.value, label: option.label),
        )
        .toList();
  }

  bool _isDateRange(String key) =>
      _filterFor(key)?.kind == ClientFilterKind.datetimeRange;

  String _valueLabelFor(String key, String value) {
    if (_isDateRange(key)) {
      final DateRangeValue parsed = DateRangeValue.parse(value);
      return parsed.isEmpty ? value : parsed.displayValue;
    }
    return _filterFor(key)?.labelForValue(value) ?? value;
  }

  String _filterLabel(String key) => _filterFor(key)?.displayLabel ?? key;

  String _sortLabel(String key) {
    for (final sort in widget.availableSorts) {
      if (sort.key == key) return sort.displayLabel;
    }
    return key;
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<ReturnOrderModel>(
      key: _tableKey,
      items: widget.returnOrders,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      isInfiniteScroll: true,
      hasMore: widget.hasMore,
      onLoadMore: widget.onLoadMore,
      searchBarActions: widget.searchBarActions,
      searchBarTrailing: widget.searchBarTrailing,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _columns,
      configKey: ReturnOrdersTable.CONFIG_KEY,
      initialPinnedColumns: const [ReturnOrdersTable.COLUMN_RETURN_ID],
      excludeFromHide: const [
        ReturnOrdersTable.COLUMN_RETURN_ID,
        ReturnOrdersTable.COLUMN_ACTIONS,
      ],
      excludeFromPin: const [
        ReturnOrdersTable.COLUMN_RETURN_ID,
        ReturnOrdersTable.COLUMN_ACTIONS,
      ],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      // Status is locked on because the page opens on the pending queue; letting
      // it be cleared would quietly turn the queue into the full archive.
      lockedFilters: const {AppStrings.FILTER_BY_STATUS},
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      isDateRangeFilter: _isDateRange,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.RETURN_ORDERS_TABLE_SEARCH_HINT,
      emptyTitle: AppStrings.RETURN_ORDERS_EMPTY_STATE_TITLE,
      emptyDescription: AppStrings.RETURN_ORDERS_EMPTY_STATE_BODY,
      emptyIcon: Icons.assignment_return_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ReturnOrderModel returnOrder,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case ReturnOrdersTable.COLUMN_RETURN_ID:
        return _textCell(returnOrder.publicId, isStrong: true);
      case ReturnOrdersTable.COLUMN_CLIENT:
        return _textCell(returnOrder.client.companyName, isStrong: true);
      case ReturnOrdersTable.COLUMN_ORDER:
        return _textCell(returnOrder.order.publicId);
      case ReturnOrdersTable.COLUMN_STATUS:
        return Center(
          child: ReturnOrderStatusBadge(status: returnOrder.status),
        );
      case ReturnOrdersTable.COLUMN_RETURN_DATE:
        return _textCell(DateFormatter.label(_iso(returnOrder.returnDate)));
      case ReturnOrdersTable.COLUMN_RAISED_BY:
        return _textCell(returnOrder.createdByName);
      case ReturnOrdersTable.COLUMN_ACTIONS:
        return _buildActions(returnOrder);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  /// A return keeps its own date, so the day is the whole message; showing the
  /// time as well would imply a precision the backend does not store.
  static String? _iso(DateTime? value) {
    if (value == null) return null;
    final String month = value.month.toString().padLeft(2, '0');
    final String day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }

  Widget _buildActions(ReturnOrderModel returnOrder) {
    final bool isBusy = widget.isMutating;

    return Align(
      alignment: Alignment.center,
      child: RowActionsMenu(
        enabled: !isBusy,
        actions: [
          RowAction(
            label: AppStrings.RETURN_ORDER_VIEW_SLIP,
            icon: Icons.receipt_long_outlined,
            blockedHint: AppStrings.RETURN_ORDER_VIEW_SLIP_BLOCKED,
            onSelected:
                returnOrder.status != ReturnOrderStatus.accepted ||
                    isBusy ||
                    widget.onViewSlip == null
                ? null
                : () => widget.onViewSlip!(returnOrder),
          ),
          RowAction(
            label: AppStrings.RETURN_ORDER_ACCEPT,
            icon: Icons.check_circle_outline_rounded,
            tone: RowActionTone.success,
            blockedHint: AppStrings.RETURN_ORDER_ACCEPT_BLOCKED,
            onSelected:
                !returnOrder.canAccept || isBusy || widget.onAccept == null
                ? null
                : () => widget.onAccept!(returnOrder),
          ),
          RowAction(
            label: AppStrings.RETURN_ORDER_REJECT,
            icon: Icons.block_outlined,
            tone: RowActionTone.error,
            blockedHint: AppStrings.RETURN_ORDER_REJECT_BLOCKED,
            onSelected:
                !returnOrder.canReject || isBusy || widget.onReject == null
                ? null
                : () => widget.onReject!(returnOrder),
          ),
          RowAction(
            label: AppStrings.RETURN_ORDER_EDIT,
            icon: Icons.edit_outlined,
            blockedHint: AppStrings.RETURN_ORDER_EDIT_BLOCKED,
            onSelected: !returnOrder.canEdit || isBusy || widget.onEdit == null
                ? null
                : () => widget.onEdit!(returnOrder),
          ),
          RowAction(
            label: AppStrings.RETURN_ORDER_UNREJECT,
            icon: Icons.undo_outlined,
            blockedHint: AppStrings.RETURN_ORDER_UNREJECT_BLOCKED,
            onSelected:
                !returnOrder.canUnreject || isBusy || widget.onUnreject == null
                ? null
                : () => widget.onUnreject!(returnOrder),
          ),
          RowAction(
            label: AppStrings.RETURN_ORDER_REVERT_ACCEPT,
            icon: Icons.undo_outlined,
            tone: RowActionTone.warning,
            blockedHint: AppStrings.RETURN_ORDER_REVERT_ACCEPT_BLOCKED,
            onSelected:
                !returnOrder.canRevertAccept ||
                    isBusy ||
                    widget.onRevertAccept == null
                ? null
                : () => widget.onRevertAccept!(returnOrder),
          ),
        ],
      ),
    );
  }

  Widget _textCell(String value, {bool isStrong = false}) {
    final String text = value.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : value;

    return Center(
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        textAlign: TextAlign.center,
        style: isStrong
            ? AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w600)
            : AppTypography.bodySmall.copyWith(color: AppColors.TEXT_SECONDARY),
      ),
    );
  }
}
