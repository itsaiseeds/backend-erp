import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/product_packaging_model.dart';

class ProductPackagingsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'product_packagings';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_PACKING_BAG_WEIGHT = 'packing_bag_weight';
  static const String COLUMN_PACKING_BAGS = 'packing_bags';
  static const String COLUMN_TOTAL_WEIGHT = 'total_weight';
  static const String COLUMN_SELLING_PRICE = 'selling_price';

  final List<ProductPackagingModel> packagings;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(ProductPackagingModel packaging)? onEdit;
  final void Function(ProductPackagingModel packaging)? onDelete;
  final void Function(ProductPackagingModel packaging)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const ProductPackagingsTable({
    super.key,
    required this.packagings,
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
    this.emptyTitle = AppStrings.PRODUCT_PACKAGINGS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PRODUCT_PACKAGINGS_EMPTY_STATE_BODY,
  });

  @override
  State<ProductPackagingsTable> createState() => ProductPackagingsTableState();
}

class ProductPackagingsTableState extends State<ProductPackagingsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: ProductPackagingsTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: ProductPackagingsTable.COLUMN_PACKING_BAG_WEIGHT,
      label: AppStrings.COLUMN_PACKING_BAG_WEIGHT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: ProductPackagingsTable.COLUMN_PACKING_BAGS,
      label: AppStrings.COLUMN_PACKING_BAGS,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: ProductPackagingsTable.COLUMN_TOTAL_WEIGHT,
      label: AppStrings.COLUMN_TOTAL_WEIGHT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: ProductPackagingsTable.COLUMN_SELLING_PRICE,
      label: AppStrings.COLUMN_SELLING_PRICE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<ProductPackagingModel>> _tableKey =
      GlobalKey<AppDataTableState<ProductPackagingModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  String _filterLabel(String filter) {
    switch (filter) {
      case AppStrings.FILTER_BY_PRODUCT:
        return AppStrings.COLUMN_PRODUCT;
      default:
        return filter;
    }
  }

  String _sortLabel(String sort) {
    switch (sort) {
      case AppStrings.SORT_BY_PRODUCT:
        return AppStrings.COLUMN_PRODUCT;
      case AppStrings.SORT_BY_PACKING_BAG_WEIGHT:
        return AppStrings.COLUMN_PACKING_BAG_WEIGHT;
      case AppStrings.SORT_BY_PACKING_BAGS:
        return AppStrings.COLUMN_PACKING_BAGS;
      case AppStrings.SORT_BY_TOTAL_WEIGHT:
        return AppStrings.COLUMN_TOTAL_WEIGHT;
      case AppStrings.SORT_BY_SELLING_PRICE:
        return AppStrings.COLUMN_SELLING_PRICE;
      default:
        return sort;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<ProductPackagingModel>(
      key: _tableKey,
      items: widget.packagings,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: ProductPackagingsTable.CONFIG_KEY,
      initialPinnedColumns: const [ProductPackagingsTable.COLUMN_PRODUCT],
      excludeFromPin: const [ProductPackagingsTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        ProductPackagingsTable.COLUMN_PRODUCT,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: const [
        AppStrings.SORT_BY_PRODUCT,
        AppStrings.SORT_BY_PACKING_BAG_WEIGHT,
        AppStrings.SORT_BY_PACKING_BAGS,
        AppStrings.SORT_BY_TOTAL_WEIGHT,
        AppStrings.SORT_BY_SELLING_PRICE,
      ],
      filterByOptions: const [AppStrings.FILTER_BY_PRODUCT],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.PRODUCT_PACKAGINGS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.inventory_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ProductPackagingModel packaging,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case ProductPackagingsTable.COLUMN_PRODUCT:
        return _textCell(packaging.productName, isStrong: true);
      case ProductPackagingsTable.COLUMN_PACKING_BAG_WEIGHT:
        return _textCell(packaging.packingBagWeight);
      case ProductPackagingsTable.COLUMN_PACKING_BAGS:
        return _textCell(packaging.packingBagsLabel);
      case ProductPackagingsTable.COLUMN_TOTAL_WEIGHT:
        return _textCell(packaging.totalWeight);
      case ProductPackagingsTable.COLUMN_SELLING_PRICE:
        return _textCell(packaging.sellingPrice);
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
                  : () => widget.onEdit!(packaging),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.delete_outline_rounded,
              tooltip: AppStrings.DELETE,
              type: IconActionType.error,
              onPressed: widget.onDelete == null
                  ? null
                  : () => widget.onDelete!(packaging),
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
