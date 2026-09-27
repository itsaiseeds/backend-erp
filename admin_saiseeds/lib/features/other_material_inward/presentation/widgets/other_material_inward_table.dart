import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/recipes_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/other_material_inward_model.dart';

class OtherMaterialInwardTable extends StatefulWidget {
  static const String CONFIG_KEY = 'other-material-inward';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_PACKET_WEIGHT = 'packet_weight';
  static const String COLUMN_PARTY = 'party';
  static const String COLUMN_QUANTITY = 'quantity';
  static const String COLUMN_EFFECTIVE_DATE = 'effective_date';

  final List<OtherMaterialInwardModel> lots;
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
  final void Function(OtherMaterialInwardModel lot)? onDelete;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const OtherMaterialInwardTable({
    super.key,
    required this.lots,
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
    this.onDelete,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.OTHER_INWARD_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.OTHER_INWARD_EMPTY_STATE_BODY,
  });

  @override
  State<OtherMaterialInwardTable> createState() =>
      OtherMaterialInwardTableState();
}

class OtherMaterialInwardTableState extends State<OtherMaterialInwardTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: OtherMaterialInwardTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: OtherMaterialInwardTable.COLUMN_PACKET_WEIGHT,
      label: AppStrings.COLUMN_PACKET_WEIGHT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: OtherMaterialInwardTable.COLUMN_PARTY,
      label: AppStrings.COLUMN_PARTY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: OtherMaterialInwardTable.COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: OtherMaterialInwardTable.COLUMN_EFFECTIVE_DATE,
      label: AppStrings.COLUMN_EFFECTIVE_DATE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<OtherMaterialInwardModel>> _tableKey =
      GlobalKey<AppDataTableState<OtherMaterialInwardModel>>();

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
    return AppDataTable<OtherMaterialInwardModel>(
      key: _tableKey,
      items: widget.lots,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: OtherMaterialInwardTable.CONFIG_KEY,
      initialPinnedColumns: const [OtherMaterialInwardTable.COLUMN_PRODUCT],
      excludeFromPin: const [OtherMaterialInwardTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        OtherMaterialInwardTable.COLUMN_PRODUCT,
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
      searchHintText: AppStrings.OTHER_INWARD_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.inventory_2_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    OtherMaterialInwardModel lot,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case OtherMaterialInwardTable.COLUMN_PRODUCT:
        return _textCell(lot.productName, isStrong: true);
      case OtherMaterialInwardTable.COLUMN_PACKET_WEIGHT:
        return _textCell(lot.packetWeight);
      case OtherMaterialInwardTable.COLUMN_PARTY:
        return _textCell(lot.partyName);
      case OtherMaterialInwardTable.COLUMN_QUANTITY:
        return _textCell(_quantityWithUnit(lot), isStrong: true);
      case OtherMaterialInwardTable.COLUMN_EFFECTIVE_DATE:
        return _textCell(DateFormatter.dayLabel(lot.effectiveDateTime));
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
                  : () => widget.onDelete!(lot),
            ),
          ],
        );
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  static String _quantityWithUnit(OtherMaterialInwardModel lot) {
    final String quantity = lot.quantity.trim();
    if (quantity.isEmpty) return quantity;

    final String unit = RecipesService.instance
            .recipeByPublicId(lot.recipePublicId)
            ?.unitType
            .trim() ??
        '';
    if (unit.isEmpty) return quantity;

    return '$quantity $unit';
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
