import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/raw_material_stock_model.dart';

class RawMaterialStockTable extends StatefulWidget {
  static const String CONFIG_KEY = 'raw-material-stock';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_INCOMING = 'incoming_kg';
  static const String COLUMN_PACKED = 'packed_kg';
  static const String COLUMN_AVAILABLE = 'available_kg';

  final List<RawMaterialStockLineModel> lines;
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

  const RawMaterialStockTable({
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
    this.emptyTitle = AppStrings.RAW_MATERIAL_STOCK_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.RAW_MATERIAL_STOCK_EMPTY_STATE_BODY,
  });

  @override
  State<RawMaterialStockTable> createState() => RawMaterialStockTableState();
}

class RawMaterialStockTableState extends State<RawMaterialStockTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: RawMaterialStockTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: RawMaterialStockTable.COLUMN_INCOMING,
      label: AppStrings.COLUMN_INCOMING_KG,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: RawMaterialStockTable.COLUMN_PACKED,
      label: AppStrings.COLUMN_PACKED_KG,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: RawMaterialStockTable.COLUMN_AVAILABLE,
      label: AppStrings.COLUMN_AVAILABLE_KG,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

  final GlobalKey<AppDataTableState<RawMaterialStockLineModel>> _tableKey =
      GlobalKey<AppDataTableState<RawMaterialStockLineModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  @override
  Widget build(BuildContext context) {
    return AppDataTable<RawMaterialStockLineModel>(
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
      configKey: RawMaterialStockTable.CONFIG_KEY,
      initialPinnedColumns: const [RawMaterialStockTable.COLUMN_PRODUCT],
      excludeFromPin: const [RawMaterialStockTable.COLUMN_PRODUCT],
      excludeFromHide: const [RawMaterialStockTable.COLUMN_PRODUCT],
      sortByOptions: const [AppStrings.SORT_BY_PRODUCT],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      searchHintText: AppStrings.RAW_MATERIAL_STOCK_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.grass_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    RawMaterialStockLineModel line,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case RawMaterialStockTable.COLUMN_PRODUCT:
        return _textCell(line.name, isStrong: true);
      case RawMaterialStockTable.COLUMN_INCOMING:
        return _textCell(line.incomingKg);
      case RawMaterialStockTable.COLUMN_PACKED:
        return _textCell(line.packedKg);
      case RawMaterialStockTable.COLUMN_AVAILABLE:
        return _textCell(line.availableKg, isStrong: true);
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
