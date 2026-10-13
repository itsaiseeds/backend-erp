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
import '../../../custom_orders/data/models/custom_order_model.dart';
import '../../../orders/presentation/widgets/order_status_badge.dart';

class RejectedLotOrdersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'rejected-lot-orders';
  static const String COLUMN_ORDER_ID = 'order_id';
  static const String COLUMN_CLIENT = 'client';
  static const String COLUMN_STATUS = 'status';
  static const String COLUMN_AMOUNT = 'amount';
  static const String COLUMN_ITEMS = 'item_count';
  static const String COLUMN_KG = 'total_kg';
  static const String COLUMN_ADDRESS = 'delivery_address';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_EXPECTED = 'expected_delivery_date';
  static const String COLUMN_PLACED = 'placed';
  static const String COLUMN_CREATED_BY = 'created_by';

  final List<CustomOrderModel> orders;
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
  final void Function(CustomOrderModel order)? onView;
  final void Function(CustomOrderModel order)? onDelete;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;

  const RejectedLotOrdersTable({
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
    this.onDelete,
    this.hasMore = false,
    this.onLoadMore,
    this.searchBarActions = const [],
  });

  @override
  State<RejectedLotOrdersTable> createState() =>
      RejectedLotOrdersTableState();
}

class RejectedLotOrdersTableState extends State<RejectedLotOrdersTable> {
  final GlobalKey<AppDataTableState<CustomOrderModel>> _tableKey =
      GlobalKey<AppDataTableState<CustomOrderModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  List<AppDataColumn> get _columns => const [
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_ORDER_ID,
      label: AppStrings.COLUMN_ORDER_ID,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_CLIENT,
      label: AppStrings.COLUMN_ORDER_CLIENT,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_ORDER_STATUS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_AMOUNT,
      label: AppStrings.COLUMN_ORDER_AMOUNT,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_ITEMS,
      label: AppStrings.COLUMN_CUSTOM_ORDER_ITEMS,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_KG,
      label: AppStrings.COLUMN_WASTE_ORDER_KG,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_ADDRESS,
      label: AppStrings.COLUMN_ORDER_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CUSTOM_ORDER_CITY,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_EXPECTED,
      label: AppStrings.COLUMN_CUSTOM_ORDER_EXPECTED,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_PLACED,
      label: AppStrings.COLUMN_ORDER_PLACED,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: RejectedLotOrdersTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_ORDER_SALES_PERSON,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
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
    for (final ClientFilterModel filter in widget.availableFilters) {
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
    for (final ClientSortModel sort in widget.availableSorts) {
      if (sort.key == key) return sort.displayLabel;
    }
    return key;
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<CustomOrderModel>(
      key: _tableKey,
      items: widget.orders,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      isInfiniteScroll: true,
      hasMore: widget.hasMore,
      onLoadMore: widget.onLoadMore,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _columns,
      configKey: RejectedLotOrdersTable.CONFIG_KEY,
      initialPinnedColumns: const [RejectedLotOrdersTable.COLUMN_ORDER_ID],
      excludeFromHide: const [
        RejectedLotOrdersTable.COLUMN_ORDER_ID,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      excludeFromPin: const [
        RejectedLotOrdersTable.COLUMN_ORDER_ID,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
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
      searchHintText: AppStrings.REJECTED_LOT_ORDERS_SEARCH_HINT,
      emptyTitle: AppStrings.REJECTED_LOT_ORDERS_EMPTY_TITLE,
      emptyDescription: AppStrings.REJECTED_LOT_ORDERS_EMPTY_BODY,
      emptyIcon: Icons.tune_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    CustomOrderModel order,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case RejectedLotOrdersTable.COLUMN_ORDER_ID:
        return _textCell(order.publicId, isStrong: true);
      case RejectedLotOrdersTable.COLUMN_CLIENT:
        return _textCell(order.clientName, isStrong: true);
      case RejectedLotOrdersTable.COLUMN_STATUS:
        return Center(child: OrderStatusBadge(status: order.statusValue));
      case RejectedLotOrdersTable.COLUMN_AMOUNT:
        return _textCell(CurrencyFormatter.rupees(order.totalAmountValue ?? 0));
      case RejectedLotOrdersTable.COLUMN_ITEMS:
        return _textCell('${order.itemCount}');
      case RejectedLotOrdersTable.COLUMN_KG:
        return _textCell(order.totalKg);
      case RejectedLotOrdersTable.COLUMN_ADDRESS:
        return _textCell(order.deliveryToLabel);
      case RejectedLotOrdersTable.COLUMN_CITY:
        return _textCell(order.cityName);
      case RejectedLotOrdersTable.COLUMN_EXPECTED:
        return _textCell(
          DateFormatter.dayLabel(order.expectedDeliveryDateTime),
        );
      case RejectedLotOrdersTable.COLUMN_PLACED:
        return _textCell(DateFormatter.instantLabel(order.createdAtDateTime));
      case RejectedLotOrdersTable.COLUMN_CREATED_BY:
        return _textCell(order.createdBy);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return _buildActions(order);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  Widget _buildActions(CustomOrderModel order) {
    final bool isBusy = widget.isMutating;

    return Align(
      alignment: Alignment.center,
      child: RowActionsMenu(
        enabled: !isBusy,
        actions: [
          RowAction(
            label: AppStrings.DELETE,
            icon: Icons.delete_outline_rounded,
            tone: RowActionTone.error,
            blockedHint: AppStrings.REJECTED_LOT_ORDER_DELETE_BLOCKED,
            onSelected:
                !order.canDeleteRejectedOrder ||
                    isBusy ||
                    widget.onDelete == null
                ? null
                : () => widget.onDelete!(order),
          ),
        ],
      ),
    );
  }

  Widget _textCell(String value, {bool isStrong = false}) {
    final String text = value.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : value;
    return Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: isStrong
          ? AppTypography.tableCellStrong
          : AppTypography.tableCell.copyWith(color: AppColors.TEXT_PRIMARY),
    );
  }
}
