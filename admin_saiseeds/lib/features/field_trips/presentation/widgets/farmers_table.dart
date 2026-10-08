import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/layout/overflow_tooltip.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/farmer_model.dart';

class FarmersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'farmers';
  static const String COLUMN_FARMER = 'farmer_name';
  static const String COLUMN_CONTACT = 'contact_number';
  static const String COLUMN_VILLAGE = 'village';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_LAND = 'land_area_bigha';
  static const String COLUMN_CROPS = 'crops';
  static const String COLUMN_IS_LEAD = 'is_lead';
  static const String COLUMN_USES_PRODUCTS = 'uses_our_products';
  static const String COLUMN_VISIT_COUNT = 'visit_count';
  static const String COLUMN_LAST_VISITED = 'last_visited_at';
  static const String COLUMN_SALES_PEOPLE = 'sales_people';

  final List<FarmerModel> farmers;
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
  final void Function(FarmerModel farmer)? onView;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const FarmersTable({
    super.key,
    required this.farmers,
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
    this.hasMore = false,
    this.onLoadMore,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.FARMERS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.FARMERS_EMPTY_STATE_BODY,
  });

  @override
  State<FarmersTable> createState() => FarmersTableState();
}

class FarmersTableState extends State<FarmersTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: FarmersTable.COLUMN_FARMER,
      label: AppStrings.COLUMN_FARMER_NAME,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_CONTACT,
      label: AppStrings.COLUMN_CONTACT_NUMBER,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_VILLAGE,
      label: AppStrings.COLUMN_VILLAGE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_LAND,
      label: AppStrings.COLUMN_LAND_AREA,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_CROPS,
      label: AppStrings.COLUMN_CROPS,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_IS_LEAD,
      label: AppStrings.COLUMN_IS_LEAD,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_USES_PRODUCTS,
      label: AppStrings.COLUMN_USES_OUR_PRODUCTS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_VISIT_COUNT,
      label: AppStrings.COLUMN_VISIT_COUNT,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_LAST_VISITED,
      label: AppStrings.COLUMN_LAST_VISITED,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FarmersTable.COLUMN_SALES_PEOPLE,
      label: AppStrings.COLUMN_SALES_PEOPLE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<FarmerModel>> _tableKey =
      GlobalKey<AppDataTableState<FarmerModel>>();

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

  bool _isDateRange(String key) =>
      _filterFor(key)?.kind == ClientFilterKind.datetimeRange;

  String _valueLabelFor(String key, String value) {
    if (_isDateRange(key)) {
      final DateRangeValue parsed = DateRangeValue.parse(value);
      return parsed.isEmpty ? value : parsed.displayValue;
    }
    return _filterFor(key)?.labelForValue(value) ?? value;
  }

  String _filterLabel(String key) => _filterFor(key)?.displayLabel ?? key;

  String _sortLabel(String key) {
    for (final sort in widget.availableSorts) {
      if (sort.key == key) return sort.displayLabel;
    }
    return key;
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<FarmerModel>(
      key: _tableKey,
      items: widget.farmers,
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
      configKey: FarmersTable.CONFIG_KEY,
      initialPinnedColumns: const [FarmersTable.COLUMN_FARMER],
      excludeFromPin: const [FarmersTable.COLUMN_FARMER],
      excludeFromHide: const [
        FarmersTable.COLUMN_FARMER,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      isDateRangeFilter: _isDateRange,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.FARMERS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.agriculture_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    FarmerModel farmer,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case FarmersTable.COLUMN_FARMER:
        return _textCell(farmer.farmerName, isStrong: true);
      case FarmersTable.COLUMN_CONTACT:
        return _textCell(farmer.contactNumber);
      case FarmersTable.COLUMN_VILLAGE:
        return _textCell(farmer.village);
      case FarmersTable.COLUMN_CITY:
        return _textCell(farmer.cityName);
      case FarmersTable.COLUMN_LAND:
        return _textCell(farmer.landAreaBigha);
      case FarmersTable.COLUMN_CROPS:
        return _listCell(farmer.cropNames);
      case FarmersTable.COLUMN_IS_LEAD:
        return Align(
          alignment: Alignment.center,
          child: Icon(
            farmer.isLead
                ? Icons.check_circle_outline_rounded
                : Icons.remove_circle_outline_rounded,
            size: AppSizes.iconMd,
            color: farmer.isLead ? AppColors.SUCCESS : AppColors.TEXT_DISABLED,
          ),
        );
      case FarmersTable.COLUMN_USES_PRODUCTS:
        return Align(
          alignment: Alignment.center,
          child: Icon(
            farmer.usesOurProducts
                ? Icons.check_circle_outline_rounded
                : Icons.remove_circle_outline_rounded,
            size: AppSizes.iconMd,
            color: farmer.usesOurProducts
                ? AppColors.SUCCESS
                : AppColors.TEXT_DISABLED,
          ),
        );
      case FarmersTable.COLUMN_VISIT_COUNT:
        return Align(
          alignment: Alignment.center,
          child: _textCell('${farmer.visitCount}'),
        );
      case FarmersTable.COLUMN_LAST_VISITED:
        return _textCell(
          DateFormatter.instantLabel(farmer.lastVisitedDateTime),
        );
      case FarmersTable.COLUMN_SALES_PEOPLE:
        return _listCell(farmer.salesPeopleNames);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Align(
          alignment: Alignment.center,
          child: RowActionsMenu(actions: _actionsFor(farmer)),
        );
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  List<RowAction> _actionsFor(FarmerModel farmer) {
    return [
      RowAction(
        label: AppStrings.VIEW_DETAILS,
        icon: Icons.visibility_outlined,
        onSelected: widget.onView == null ? null : () => widget.onView!(farmer),
      ),
    ];
  }

  /// A list reads as one comma-joined line so the row keeps its height; the
  /// full set is on hover when it does not fit.
  Widget _listCell(List<String> values) {
    final List<String> present = values
        .map((value) => value.trim())
        .where((value) => value.isNotEmpty)
        .toList();

    if (present.isEmpty) return _textCell('');

    final String joined = present.join(', ');
    final TextStyle style = AppTypography.tableCell.copyWith(
      color: AppColors.TEXT_PRIMARY,
    );

    return OverflowTooltip(
      text: joined,
      style: style,
      child: Text(
        joined,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: style,
      ),
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
