import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/purchase_tracking_model.dart';

class PurchaseTrackingTable extends StatefulWidget {
  static const String CONFIG_KEY = 'purchase-tracking';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_COMPANY = 'company_name';
  static const String COLUMN_QUANTITY = 'quantity';
  static const String COLUMN_UNIT = 'unit';
  static const String COLUMN_PRICE = 'price';
  static const String COLUMN_CREATED_AT = 'created_at';
  static const String COLUMN_CREATED_BY = 'created_by';

  final List<PurchaseTrackingModel> entries;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final void Function(PurchaseTrackingModel entry)? onView;
  final void Function(PurchaseTrackingModel entry)? onEdit;
  final void Function(PurchaseTrackingModel entry)? onDelete;
  final bool isMutating;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const PurchaseTrackingTable({
    super.key,
    required this.entries,
    required this.isLoading,
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
    this.onDelete,
    this.isMutating = false,
    this.hasMore = false,
    this.onLoadMore,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.PURCHASE_TRACKING_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PURCHASE_TRACKING_EMPTY_STATE_BODY,
  });

  @override
  State<PurchaseTrackingTable> createState() => PurchaseTrackingTableState();
}

class PurchaseTrackingTableState extends State<PurchaseTrackingTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_NAME,
      label: AppStrings.FIELD_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_COMPANY,
      label: AppStrings.COLUMN_COMPANY_NAME,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_UNIT,
      label: AppStrings.COLUMN_UNIT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_PRICE,
      label: AppStrings.COLUMN_PRICE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_CREATED_AT,
      label: AppStrings.COLUMN_CREATED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: PurchaseTrackingTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<PurchaseTrackingModel>> _tableKey =
      GlobalKey<AppDataTableState<PurchaseTrackingModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

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

  String _valueLabelFor(String key, String value) =>
      _filterFor(key)?.labelForValue(value) ?? value;

  String _filterLabel(String key) => _filterFor(key)?.displayLabel ?? key;

  String _sortLabel(String key) {
    for (final sort in widget.availableSorts) {
      if (sort.key == key) return sort.displayLabel;
    }
    return key;
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<PurchaseTrackingModel>(
      key: _tableKey,
      items: widget.entries,
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
      columns: _COLUMNS,
      configKey: PurchaseTrackingTable.CONFIG_KEY,
      initialPinnedColumns: const [PurchaseTrackingTable.COLUMN_NAME],
      excludeFromPin: const [PurchaseTrackingTable.COLUMN_NAME],
      excludeFromHide: const [
        PurchaseTrackingTable.COLUMN_NAME,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.PURCHASE_TRACKING_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.shopping_bag_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    PurchaseTrackingModel entry,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case PurchaseTrackingTable.COLUMN_NAME:
        return _textCell(entry.name, isStrong: true);
      case PurchaseTrackingTable.COLUMN_COMPANY:
        return _textCell(
          entry.hasCompanyName
              ? entry.companyName
              : AppStrings.PURCHASE_TRACKING_COMPANY_MISSING,
        );
      case PurchaseTrackingTable.COLUMN_QUANTITY:
        return _textCell(entry.quantity);
      case PurchaseTrackingTable.COLUMN_UNIT:
        return _textCell(entry.unit);
      case PurchaseTrackingTable.COLUMN_PRICE:
        return _textCell(
          entry.hasPrice
              ? entry.price!
              : AppStrings.PURCHASE_TRACKING_PRICE_MISSING,
        );
      case PurchaseTrackingTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(entry.createdAt));
      case PurchaseTrackingTable.COLUMN_CREATED_BY:
        return _textCell(entry.createdByName);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Align(
          alignment: Alignment.center,
          child: RowActionsMenu(
            enabled: !widget.isMutating,
            actions: [
              RowAction(
                label: AppStrings.PURCHASE_TRACKING_EDIT,
                icon: Icons.edit_outlined,
                tone: RowActionTone.neutral,
                onSelected: widget.isMutating || widget.onEdit == null
                    ? null
                    : () => widget.onEdit!(entry),
              ),
              RowAction(
                label: AppStrings.DELETE,
                icon: Icons.delete_outline_rounded,
                tone: RowActionTone.error,
                onSelected: widget.isMutating || widget.onDelete == null
                    ? null
                    : () => widget.onDelete!(entry),
              ),
            ],
          ),
        );
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
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
