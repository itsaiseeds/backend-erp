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
import '../../data/models/waste_model.dart';

class WasteManagementTable extends StatefulWidget {
  static const String CONFIG_KEY = 'waste-management';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_QUANTITY = 'quantity_kg';
  static const String COLUMN_REASON = 'reason';
  static const String COLUMN_CREATED_AT = 'created_at';
  static const String COLUMN_CREATED_BY = 'created_by';

  final List<WasteModel> wastes;
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
  final void Function(WasteModel waste)? onView;
  final void Function(WasteModel waste)? onEdit;
  final void Function(WasteModel waste)? onDelete;
  final bool isMutating;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const WasteManagementTable({
    super.key,
    required this.wastes,
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
    this.emptyTitle = AppStrings.WASTE_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.WASTE_EMPTY_STATE_BODY,
  });

  @override
  State<WasteManagementTable> createState() => WasteManagementTableState();
}

class WasteManagementTableState extends State<WasteManagementTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: WasteManagementTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: WasteManagementTable.COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY_KG,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: WasteManagementTable.COLUMN_REASON,
      label: AppStrings.COLUMN_REASON,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: WasteManagementTable.COLUMN_CREATED_AT,
      label: AppStrings.COLUMN_CREATED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: WasteManagementTable.COLUMN_CREATED_BY,
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

  final GlobalKey<AppDataTableState<WasteModel>> _tableKey =
      GlobalKey<AppDataTableState<WasteModel>>();

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
    return AppDataTable<WasteModel>(
      key: _tableKey,
      items: widget.wastes,
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
      configKey: WasteManagementTable.CONFIG_KEY,
      initialPinnedColumns: const [WasteManagementTable.COLUMN_PRODUCT],
      excludeFromPin: const [WasteManagementTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        WasteManagementTable.COLUMN_PRODUCT,
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
      searchHintText: AppStrings.WASTE_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.delete_sweep_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(BuildContext context, WasteModel waste, AppDataColumn col) {
    switch (col.id) {
      case WasteManagementTable.COLUMN_PRODUCT:
        return _textCell(waste.productName, isStrong: true);
      case WasteManagementTable.COLUMN_QUANTITY:
        return _textCell(waste.quantityKg);
      case WasteManagementTable.COLUMN_REASON:
        return _textCell(
          waste.hasReason ? waste.reason : AppStrings.WASTE_REASON_MISSING,
        );
      case WasteManagementTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(waste.createdAt));
      case WasteManagementTable.COLUMN_CREATED_BY:
        return _textCell(waste.createdByName);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Align(
          alignment: Alignment.center,
          child: RowActionsMenu(
            enabled: !widget.isMutating,
            actions: [
              RowAction(
                label: AppStrings.WASTE_EDIT,
                icon: Icons.edit_outlined,
                tone: RowActionTone.neutral,
                onSelected: widget.isMutating || widget.onEdit == null
                    ? null
                    : () => widget.onEdit!(waste),
              ),
              RowAction(
                label: AppStrings.DELETE,
                icon: Icons.delete_outline_rounded,
                tone: RowActionTone.error,
                onSelected: widget.isMutating || widget.onDelete == null
                    ? null
                    : () => widget.onDelete!(waste),
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
