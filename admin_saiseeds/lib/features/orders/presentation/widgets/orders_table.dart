import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/order_model.dart';
import 'order_status_badge.dart';

class OrdersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'orders';
  static const String COLUMN_ORDER_ID = 'order_id';
  static const String COLUMN_CLIENT = 'client';
  static const String COLUMN_STATUS = 'status';
  static const String COLUMN_AMOUNT = 'amount';
  static const String COLUMN_ADDRESS = 'delivery_address';
  static const String COLUMN_PLACED = 'placed';
  static const String COLUMN_SALES_PERSON = 'sales_person';
  static const String COLUMN_VERIFIED_BY = 'verified_by';
  static const String COLUMN_CLIENT_ADDED_BY = 'client_created_by';
  static const String COLUMN_ORDER_ACTIONS = 'order_actions';

  final List<OrderModel> orders;
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
  final void Function(OrderModel order)? onView;
  final void Function(OrderModel order)? onVerify;
  final void Function(OrderModel order)? onUnverify;
  final void Function(OrderModel order)? onHold;
  final void Function(OrderModel order)? onReject;
  final List<Widget> searchBarActions;
  final Widget? searchBarTrailing;

  const OrdersTable({
    super.key,
    required this.orders,
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
    this.onVerify,
    this.onUnverify,
    this.onHold,
    this.onReject,
    this.searchBarActions = const [],
    this.searchBarTrailing,
  });

  @override
  State<OrdersTable> createState() => OrdersTableState();
}

class OrdersTableState extends State<OrdersTable> {
  final GlobalKey<AppDataTableState<OrderModel>> _tableKey =
      GlobalKey<AppDataTableState<OrderModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  List<AppDataColumn> get _columns => const [
    AppDataColumn(
      id: OrdersTable.COLUMN_ORDER_ID,
      label: AppStrings.COLUMN_ORDER_ID,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_CLIENT,
      label: AppStrings.COLUMN_ORDER_CLIENT,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_ORDER_STATUS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_AMOUNT,
      label: AppStrings.COLUMN_ORDER_AMOUNT,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_ADDRESS,
      label: AppStrings.COLUMN_ORDER_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_PLACED,
      label: AppStrings.COLUMN_ORDER_PLACED,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_SALES_PERSON,
      label: AppStrings.COLUMN_ORDER_SALES_PERSON,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_VERIFIED_BY,
      label: AppStrings.COLUMN_ORDER_VERIFIED_BY,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_CLIENT_ADDED_BY,
      label: AppStrings.COLUMN_ORDER_CLIENT_ONBOARDED_BY,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: OrdersTable.COLUMN_ORDER_ACTIONS,
      label: AppStrings.COLUMN_ORDER_ACTIONS,
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
    return AppDataTable<OrderModel>(
      key: _tableKey,
      items: widget.orders,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      searchBarTrailing: widget.searchBarTrailing,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _columns,
      configKey: OrdersTable.CONFIG_KEY,
      initialPinnedColumns: const [OrdersTable.COLUMN_ORDER_ID],
      excludeFromHide: const [
        OrdersTable.COLUMN_ORDER_ID,
        OrdersTable.COLUMN_ORDER_ACTIONS,
      ],
      excludeFromPin: const [
        OrdersTable.COLUMN_ORDER_ID,
        OrdersTable.COLUMN_ORDER_ACTIONS,
      ],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      isDateRangeFilter: _isDateRange,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.ORDERS_TABLE_SEARCH_HINT,
      emptyTitle: AppStrings.ORDERS_EMPTY_STATE_TITLE,
      emptyDescription: AppStrings.ORDERS_EMPTY_STATE_BODY,
      emptyIcon: Icons.receipt_long_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(BuildContext context, OrderModel order, AppDataColumn col) {
    switch (col.id) {
      case OrdersTable.COLUMN_ORDER_ID:
        return _textCell(order.publicId, isStrong: true);
      case OrdersTable.COLUMN_CLIENT:
        return _textCell(order.client.name, isStrong: true);
      case OrdersTable.COLUMN_STATUS:
        return Center(child: OrderStatusBadge(status: order.status));
      case OrdersTable.COLUMN_AMOUNT:
        return _textCell(CurrencyFormatter.rupees(order.totalAmount));
      case OrdersTable.COLUMN_ADDRESS:
        return _textCell(order.deliveryAddress);
      case OrdersTable.COLUMN_PLACED:
        return _textCell(DateFormatter.instantLabel(order.createdAt));
      case OrdersTable.COLUMN_SALES_PERSON:
        return _textCell(order.createdBy);
      case OrdersTable.COLUMN_VERIFIED_BY:
        return _textCell(order.verifiedBy);
      case OrdersTable.COLUMN_CLIENT_ADDED_BY:
        return _textCell(order.clientCreatedBy);
      case OrdersTable.COLUMN_ORDER_ACTIONS:
        return _buildOrderActions(order);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  Widget _buildOrderActions(OrderModel order) {
    final bool isBusy = widget.isMutating;

    return Align(
      alignment: Alignment.center,
      child: RowActionsMenu(
        enabled: !isBusy,
        actions: [
          RowAction(
            label: AppStrings.ORDER_VERIFY,
            icon: Icons.verified_outlined,
            tone: RowActionTone.success,
            blockedHint: AppStrings.ORDER_VERIFY_BLOCKED,
            onSelected: !order.canVerify || isBusy || widget.onVerify == null
                ? null
                : () => widget.onVerify!(order),
          ),
          RowAction(
            label: AppStrings.ORDER_UNVERIFY,
            icon: Icons.undo_outlined,
            blockedHint: AppStrings.ORDER_UNVERIFY_BLOCKED,
            onSelected:
                !order.canUnverify || isBusy || widget.onUnverify == null
                ? null
                : () => widget.onUnverify!(order),
          ),
          RowAction(
            label: AppStrings.ORDER_HOLD,
            icon: Icons.pause_circle_outline,
            tone: RowActionTone.warning,
            blockedHint: AppStrings.ORDER_HOLD_BLOCKED,
            onSelected: !order.canHold || isBusy || widget.onHold == null
                ? null
                : () => widget.onHold!(order),
          ),
          RowAction(
            label: AppStrings.ORDER_REJECT,
            icon: Icons.block_outlined,
            tone: RowActionTone.error,
            blockedHint: AppStrings.ORDER_REJECT_BLOCKED,
            onSelected: !order.canReject || isBusy || widget.onReject == null
                ? null
                : () => widget.onReject!(order),
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
