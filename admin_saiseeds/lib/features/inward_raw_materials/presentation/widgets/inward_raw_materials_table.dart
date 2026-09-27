import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/inward_raw_material_model.dart';

class InwardRawMaterialsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'inward-raw-materials';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_PARTY = 'party';
  static const String COLUMN_QUANTITY = 'quantity_kg';
  static const String COLUMN_STATUS = 'status';
  static const String COLUMN_LAB_DATE = 'lab_sampling_date';
  static const String COLUMN_EFFECTIVE_DATE = 'effective_date';

  final List<InwardRawMaterialModel> lots;
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
  final void Function(InwardRawMaterialModel lot)? onView;
  final void Function(InwardRawMaterialModel lot)? onDelete;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const InwardRawMaterialsTable({
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
    this.onView,
    this.onDelete,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.INWARD_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.INWARD_EMPTY_STATE_BODY,
  });

  @override
  State<InwardRawMaterialsTable> createState() =>
      InwardRawMaterialsTableState();
}

class InwardRawMaterialsTableState extends State<InwardRawMaterialsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_PARTY,
      label: AppStrings.COLUMN_PARTY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY_KG,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_STATUS,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_LAB_DATE,
      label: AppStrings.COLUMN_LAB_SAMPLING_DATE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: InwardRawMaterialsTable.COLUMN_EFFECTIVE_DATE,
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

  final GlobalKey<AppDataTableState<InwardRawMaterialModel>> _tableKey =
      GlobalKey<AppDataTableState<InwardRawMaterialModel>>();

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
    return AppDataTable<InwardRawMaterialModel>(
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
      configKey: InwardRawMaterialsTable.CONFIG_KEY,
      initialPinnedColumns: const [InwardRawMaterialsTable.COLUMN_PRODUCT],
      excludeFromPin: const [InwardRawMaterialsTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        InwardRawMaterialsTable.COLUMN_PRODUCT,
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
      searchHintText: AppStrings.INWARD_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.local_shipping_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    InwardRawMaterialModel lot,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case InwardRawMaterialsTable.COLUMN_PRODUCT:
        return _textCell(lot.productName, isStrong: true);
      case InwardRawMaterialsTable.COLUMN_PARTY:
        return _textCell(lot.partyName);
      case InwardRawMaterialsTable.COLUMN_QUANTITY:
        return _textCell(lot.quantityKg);
      case InwardRawMaterialsTable.COLUMN_STATUS:
        return AppBadge(
          label: lot.statusLabel.isEmpty
              ? AppStrings.STATUS_LAB_TESTING
              : lot.statusLabel,
          variant: lot.isInUse
              ? AppBadgeVariant.success
              : AppBadgeVariant.warning,
        );
      case InwardRawMaterialsTable.COLUMN_LAB_DATE:
        return _textCell(DateFormatter.dayLabel(lot.labSamplingDateTime));
      case InwardRawMaterialsTable.COLUMN_EFFECTIVE_DATE:
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
