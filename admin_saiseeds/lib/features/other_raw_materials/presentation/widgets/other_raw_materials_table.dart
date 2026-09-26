import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/other_material_recipe_model.dart';

class OtherRawMaterialsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'other-raw-materials';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_MATERIAL_TYPE = 'material_type';
  static const String COLUMN_PACKET_WEIGHT = 'packet_weight';
  static const String COLUMN_QUANTITY = 'quantity';
  static const String COLUMN_UNIT = 'unit_type';

  final List<OtherMaterialRecipeModel> recipes;
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
  final void Function(OtherMaterialRecipeModel recipe)? onView;
  final void Function(OtherMaterialRecipeModel recipe)? onDelete;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const OtherRawMaterialsTable({
    super.key,
    required this.recipes,
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
    this.onDelete,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.RECIPE_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.RECIPE_EMPTY_STATE_BODY,
  });

  @override
  State<OtherRawMaterialsTable> createState() => OtherRawMaterialsTableState();
}

class OtherRawMaterialsTableState extends State<OtherRawMaterialsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: OtherRawMaterialsTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: OtherRawMaterialsTable.COLUMN_MATERIAL_TYPE,
      label: AppStrings.COLUMN_MATERIAL_TYPE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: OtherRawMaterialsTable.COLUMN_PACKET_WEIGHT,
      label: AppStrings.COLUMN_PACKET_WEIGHT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: OtherRawMaterialsTable.COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: OtherRawMaterialsTable.COLUMN_UNIT,
      label: AppStrings.COLUMN_UNIT_TYPE,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<OtherMaterialRecipeModel>> _tableKey =
      GlobalKey<AppDataTableState<OtherMaterialRecipeModel>>();

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
    return AppDataTable<OtherMaterialRecipeModel>(
      key: _tableKey,
      items: widget.recipes,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: OtherRawMaterialsTable.CONFIG_KEY,
      initialPinnedColumns: const [OtherRawMaterialsTable.COLUMN_PRODUCT],
      excludeFromPin: const [OtherRawMaterialsTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        OtherRawMaterialsTable.COLUMN_PRODUCT,
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
      searchHintText: AppStrings.RECIPE_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.layers_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    OtherMaterialRecipeModel recipe,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case OtherRawMaterialsTable.COLUMN_PRODUCT:
        return _textCell(recipe.productName, isStrong: true);
      case OtherRawMaterialsTable.COLUMN_MATERIAL_TYPE:
        return _textCell(recipe.materialTypeName);
      case OtherRawMaterialsTable.COLUMN_PACKET_WEIGHT:
        return _textCell(recipe.packetWeight);
      case OtherRawMaterialsTable.COLUMN_QUANTITY:
        return _textCell(recipe.quantity, isStrong: true);
      case OtherRawMaterialsTable.COLUMN_UNIT:
        return _textCell(recipe.unitType);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            OutlinedActionButton(
              label: AppStrings.DELETE,
              icon: Icons.delete_outline_rounded,
              tone: OutlinedActionTone.error,
              onPressed: widget.onDelete == null
                  ? null
                  : () => widget.onDelete!(recipe),
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
