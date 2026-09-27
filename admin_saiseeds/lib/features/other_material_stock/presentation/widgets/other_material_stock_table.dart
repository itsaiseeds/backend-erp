import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/other_material_stock_model.dart';

class OtherMaterialStockTable extends StatefulWidget {
  static const String CONFIG_KEY = 'other-material-stock';
  static const String COLUMN_MATERIAL_TYPE = 'material_type';
  static const String COLUMN_UNIT = 'unit_type';
  static const String COLUMN_ON_HAND = 'on_hand';

  final List<OtherMaterialStockLineModel> lines;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final List<Widget> searchBarActions;
  final Widget? searchBarTrailing;
  final String emptyTitle;
  final String emptyDescription;

  const OtherMaterialStockTable({
    super.key,
    required this.lines,
    required this.isLoading,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.searchBarActions = const [],
    this.searchBarTrailing,
    this.emptyTitle = AppStrings.OTHER_MATERIAL_STOCK_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.OTHER_MATERIAL_STOCK_EMPTY_STATE_BODY,
  });

  @override
  State<OtherMaterialStockTable> createState() =>
      OtherMaterialStockTableState();
}

class OtherMaterialStockTableState extends State<OtherMaterialStockTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: OtherMaterialStockTable.COLUMN_MATERIAL_TYPE,
      label: AppStrings.COLUMN_MATERIAL_TYPE,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: OtherMaterialStockTable.COLUMN_UNIT,
      label: AppStrings.COLUMN_UNIT_TYPE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: OtherMaterialStockTable.COLUMN_ON_HAND,
      label: AppStrings.COLUMN_ON_HAND,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

  final GlobalKey<AppDataTableState<OtherMaterialStockLineModel>> _tableKey =
      GlobalKey<AppDataTableState<OtherMaterialStockLineModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  // The endpoint sends no available_filters, so the material-type options
  // are derived from the rows already on screen.
  List<FilterValueOption> _valueOptionsFor(String key) {
    if (key != AppStrings.FILTER_BY_MATERIAL_TYPE) return const [];

    final List<String> names =
        widget.lines
            .map((line) => line.materialTypeName.trim())
            .where((name) => name.isNotEmpty)
            .toSet()
            .toList()
          ..sort();
    return names
        .map((name) => FilterValueOption(value: name, label: name))
        .toList();
  }

  static String _filterLabel(String key) =>
      key == AppStrings.FILTER_BY_MATERIAL_TYPE
      ? AppStrings.FILTER_LABEL_MATERIAL_TYPE
      : key;

  static String _sortLabel(String key) =>
      key == AppStrings.SORT_BY_MATERIAL_TYPE
      ? AppStrings.SORT_LABEL_MATERIAL_TYPE
      : key;

  @override
  Widget build(BuildContext context) {
    return AppDataTable<OtherMaterialStockLineModel>(
      key: _tableKey,
      items: widget.lines,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      searchBarTrailing: widget.searchBarTrailing,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: OtherMaterialStockTable.CONFIG_KEY,
      initialPinnedColumns: const [
        OtherMaterialStockTable.COLUMN_MATERIAL_TYPE,
      ],
      excludeFromPin: const [OtherMaterialStockTable.COLUMN_MATERIAL_TYPE],
      excludeFromHide: const [OtherMaterialStockTable.COLUMN_MATERIAL_TYPE],
      sortByOptions: const [AppStrings.SORT_BY_MATERIAL_TYPE],
      filterByOptions: const [AppStrings.FILTER_BY_MATERIAL_TYPE],
      filterValueOptions: _valueOptionsFor,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      searchHintText: AppStrings.OTHER_MATERIAL_STOCK_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.layers_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    OtherMaterialStockLineModel line,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case OtherMaterialStockTable.COLUMN_MATERIAL_TYPE:
        return _textCell(line.materialTypeName, isStrong: true);
      case OtherMaterialStockTable.COLUMN_UNIT:
        return _textCell(line.unitType);
      case OtherMaterialStockTable.COLUMN_ON_HAND:
        return _textCell(_onHandWithUnit(line), isStrong: true);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  static String _onHandWithUnit(OtherMaterialStockLineModel line) {
    final String onHand = line.onHand.trim();
    if (onHand.isEmpty) return onHand;

    final String unit = line.unitType.trim();
    if (unit.isEmpty) return onHand;

    return '$onHand $unit';
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
