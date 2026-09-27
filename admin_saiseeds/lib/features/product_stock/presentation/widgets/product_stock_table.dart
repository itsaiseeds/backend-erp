import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
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

  // The endpoint sends no available_filters, so the options are derived
  // from the rows already on screen.
  List<FilterValueOption> _valueOptionsFor(String key) {
    if (key == AppStrings.FILTER_BY_TYPE) {
      return const [
        FilterValueOption(
          value: AppStrings.STOCK_KIND_BAG,
          label: AppStrings.STOCK_KIND_BAG,
        ),
        FilterValueOption(
          value: AppStrings.STOCK_KIND_LOOSE,
          label: AppStrings.STOCK_KIND_LOOSE,
        ),
      ];
    }

    if (key == AppStrings.FILTER_BY_PRODUCT) {
      final List<String> names =
          widget.lines
              .map((line) => line.name.trim())
              .where((name) => name.isNotEmpty)
              .toSet()
              .toList()
            ..sort();
      return names
          .map((name) => FilterValueOption(value: name, label: name))
          .toList();
    }

    return const [];
  }

  static String _filterLabel(String key) {
    switch (key) {
      case AppStrings.FILTER_BY_PRODUCT:
        return AppStrings.FILTER_LABEL_PRODUCT;
      case AppStrings.FILTER_BY_TYPE:
        return AppStrings.FILTER_LABEL_TYPE;
      default:
        return key;
    }
  }

  static String _sortLabel(String key) {
    switch (key) {
      case AppStrings.SORT_BY_PRODUCT:
        return AppStrings.SORT_LABEL_PRODUCT;
      case AppStrings.SORT_BY_PACKET_WEIGHT:
        return AppStrings.SORT_LABEL_PACKET_WEIGHT;
      default:
        return key;
    }
  }

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
      filterByOptions: const [
        AppStrings.FILTER_BY_PRODUCT,
        AppStrings.FILTER_BY_TYPE,
      ],
      filterValueOptions: _valueOptionsFor,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
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
        return _productCell(line);
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

  Widget _productCell(ProductStockLineModel line) {
    final String name = line.name.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : line.name;

    if (!line.hasPacketsPerBag) return _textCell(name, isStrong: true);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Flexible(
          child: Text(
            name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.tableCellStrong,
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Text(
          '(${line.packetsPerBag} ${AppStrings.PACKETS_PER_BAG_SUFFIX})',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.tableCell.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      ],
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
