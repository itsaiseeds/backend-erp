import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/product_model.dart';

class ProductsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'products';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_CROP = 'crop';
  static const String COLUMN_BUYING_PRICE = 'buying_price';
  static const String COLUMN_SELLING_PRICE = 'selling_price';
  static const String COLUMN_MARGIN_PER_BAG = 'margin_per_bag';

  final List<ProductModel> products;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(ProductModel product)? onEdit;
  final void Function(ProductModel product)? onDelete;
  final void Function(ProductModel product)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const ProductsTable({
    super.key,
    required this.products,
    required this.isLoading,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.onEdit,
    this.onDelete,
    this.onView,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.PRODUCTS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PRODUCTS_EMPTY_STATE_BODY,
  });

  @override
  State<ProductsTable> createState() => ProductsTableState();
}

class ProductsTableState extends State<ProductsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: ProductsTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: ProductsTable.COLUMN_CROP,
      label: AppStrings.COLUMN_CROP,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: ProductsTable.COLUMN_BUYING_PRICE,
      label: AppStrings.COLUMN_BUYING_PRICE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: ProductsTable.COLUMN_SELLING_PRICE,
      label: AppStrings.COLUMN_SELLING_PRICE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: ProductsTable.COLUMN_MARGIN_PER_BAG,
      label: AppStrings.COLUMN_MARGIN_PER_BAG,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<ProductModel>> _tableKey =
      GlobalKey<AppDataTableState<ProductModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  String _filterLabel(String filter) {
    switch (filter) {
      case AppStrings.FILTER_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.FILTER_BY_CROP:
        return AppStrings.COLUMN_CROP;
      default:
        return filter;
    }
  }

  String _sortLabel(String sort) {
    switch (sort) {
      case AppStrings.SORT_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.SORT_BY_BUYING_PRICE:
        return AppStrings.COLUMN_BUYING_PRICE;
      case AppStrings.SORT_BY_SELLING_PRICE:
        return AppStrings.COLUMN_SELLING_PRICE;
      case AppStrings.SORT_BY_MARGIN_PER_BAG:
        return AppStrings.COLUMN_MARGIN_PER_BAG;
      default:
        return sort;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<ProductModel>(
      key: _tableKey,
      items: widget.products,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: ProductsTable.CONFIG_KEY,
      initialPinnedColumns: const [ProductsTable.COLUMN_NAME],
      excludeFromPin: const [ProductsTable.COLUMN_NAME],
      excludeFromHide: const [
        ProductsTable.COLUMN_NAME,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: const [
        AppStrings.SORT_BY_NAME,
        AppStrings.SORT_BY_BUYING_PRICE,
        AppStrings.SORT_BY_SELLING_PRICE,
        AppStrings.SORT_BY_MARGIN_PER_BAG,
      ],
      filterByOptions: const [
        AppStrings.FILTER_BY_NAME,
        AppStrings.FILTER_BY_CROP,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.PRODUCTS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.inventory_2_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ProductModel product,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case ProductsTable.COLUMN_NAME:
        return _textCell(product.name, isStrong: true);
      case ProductsTable.COLUMN_CROP:
        return _textCell(product.cropName);
      case ProductsTable.COLUMN_BUYING_PRICE:
        return _textCell(product.buyingPrice);
      case ProductsTable.COLUMN_SELLING_PRICE:
        return _textCell(product.sellingPrice);
      case ProductsTable.COLUMN_MARGIN_PER_BAG:
        return _textCell(product.marginPerBag);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            IconActionButton(
              icon: Icons.edit_outlined,
              tooltip: AppStrings.EDIT,
              onPressed: widget.onEdit == null
                  ? null
                  : () => widget.onEdit!(product),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.delete_outline_rounded,
              tooltip: AppStrings.DELETE,
              type: IconActionType.error,
              onPressed: widget.onDelete == null
                  ? null
                  : () => widget.onDelete!(product),
            ),
          ],
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
