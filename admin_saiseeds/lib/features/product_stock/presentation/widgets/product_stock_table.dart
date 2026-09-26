import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/product_stock_line_model.dart';

class ProductStockTable extends StatefulWidget {
  static const String CONFIG_KEY = 'product-stock';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_PACKET_WEIGHT = 'packet_weight';
  static const String COLUMN_TYPE = 'type';
  static const String COLUMN_ON_HAND = 'on_hand';
  static const String COLUMN_RESERVED = 'reserved';
  static const String COLUMN_CONSUMED = 'consumed';
  static const String COLUMN_AVAILABLE = 'available';

  final List<ProductStockLineModel> lines;
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

  const ProductStockTable({
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
    this.emptyTitle = AppStrings.PRODUCT_STOCK_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PRODUCT_STOCK_EMPTY_STATE_BODY,
  });

  @override
  State<ProductStockTable> createState() => ProductStockTableState();
}

class ProductStockTableState extends State<ProductStockTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: ProductStockTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_PACKET_WEIGHT,
      label: AppStrings.COLUMN_PACKET_WEIGHT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_TYPE,
      label: AppStrings.COLUMN_STOCK_TYPE,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_ON_HAND,
      label: AppStrings.COLUMN_STOCK_ON_HAND,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_RESERVED,
      label: AppStrings.COLUMN_STOCK_RESERVED,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_CONSUMED,
      label: AppStrings.COLUMN_STOCK_CONSUMED,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: ProductStockTable.COLUMN_AVAILABLE,
      label: AppStrings.COLUMN_STOCK_AVAILABLE,
      width: AppSizes.tableColumnWidthNarrow,
    ),
  ];

  final GlobalKey<AppDataTableState<ProductStockLineModel>> _tableKey =
      GlobalKey<AppDataTableState<ProductStockLineModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  @override
  Widget build(BuildContext context) {
    return AppDataTable<ProductStockLineModel>(
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
      configKey: ProductStockTable.CONFIG_KEY,
      initialPinnedColumns: const [ProductStockTable.COLUMN_PRODUCT],
      excludeFromPin: const [ProductStockTable.COLUMN_PRODUCT],
      excludeFromHide: const [ProductStockTable.COLUMN_PRODUCT],
      sortByOptions: const [
        AppStrings.SORT_BY_PRODUCT,
        AppStrings.SORT_BY_PACKET_WEIGHT,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      searchHintText: AppStrings.PRODUCT_STOCK_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.inventory_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ProductStockLineModel line,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case ProductStockTable.COLUMN_PRODUCT:
        return _textCell(line.name, isStrong: true);
      case ProductStockTable.COLUMN_PACKET_WEIGHT:
        return _textCell(line.packetWeight);
      case ProductStockTable.COLUMN_TYPE:
        return AppBadge(
          label: line.isBag
              ? AppStrings.STOCK_KIND_BAG
              : AppStrings.STOCK_KIND_LOOSE,
          variant: line.isBag ? AppBadgeVariant.info : AppBadgeVariant.neutral,
        );
      case ProductStockTable.COLUMN_ON_HAND:
        return _textCell('${line.onHand}');
      case ProductStockTable.COLUMN_RESERVED:
        return _textCell('${line.reserved}');
      case ProductStockTable.COLUMN_CONSUMED:
        return _textCell('${line.consumed}');
      case ProductStockTable.COLUMN_AVAILABLE:
        return _textCell('${line.available}', isStrong: true);
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
