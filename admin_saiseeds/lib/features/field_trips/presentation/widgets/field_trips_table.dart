import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/field_trip_model.dart';
import 'field_trip_status_badge.dart';

class FieldTripsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'field-trips';
  static const String COLUMN_TRIP_ID = 'public_id';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_VILLAGE = 'village';
  static const String COLUMN_SALES_PERSON = 'sales_person';
  static const String COLUMN_STATUS = 'status';
  static const String COLUMN_EXPECTED_START = 'expected_start_at';
  static const String COLUMN_EXPECTED_END = 'expected_end_at';
  static const String COLUMN_STARTED_AT = 'started_at';
  static const String COLUMN_ENDED_AT = 'ended_at';
  static const String COLUMN_FARMER_VISITS = 'farmer_visit_count';

  final List<FieldTripModel> trips;
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
  final void Function(FieldTripModel trip)? onView;
  final void Function(FieldTripModel trip)? onEdit;
  final void Function(FieldTripModel trip)? onApprove;
  final void Function(FieldTripModel trip)? onUnapprove;
  final void Function(FieldTripModel trip)? onDelete;
  final bool isMutating;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const FieldTripsTable({
    super.key,
    required this.trips,
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
    this.onEdit,
    this.onApprove,
    this.onUnapprove,
    this.onDelete,
    this.isMutating = false,
    this.hasMore = false,
    this.onLoadMore,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.FIELD_TRIPS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.FIELD_TRIPS_EMPTY_STATE_BODY,
  });

  @override
  State<FieldTripsTable> createState() => FieldTripsTableState();
}

class FieldTripsTableState extends State<FieldTripsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: FieldTripsTable.COLUMN_TRIP_ID,
      label: AppStrings.COLUMN_TRIP_ID,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_VILLAGE,
      label: AppStrings.COLUMN_VILLAGE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_SALES_PERSON,
      label: AppStrings.COLUMN_SALES_PERSON,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_STATUS,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_EXPECTED_START,
      label: AppStrings.COLUMN_EXPECTED_START,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_EXPECTED_END,
      label: AppStrings.COLUMN_EXPECTED_END,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_STARTED_AT,
      label: AppStrings.COLUMN_STARTED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_ENDED_AT,
      label: AppStrings.COLUMN_ENDED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: FieldTripsTable.COLUMN_FARMER_VISITS,
      label: AppStrings.COLUMN_FARMER_VISITS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<FieldTripModel>> _tableKey =
      GlobalKey<AppDataTableState<FieldTripModel>>();

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
    return AppDataTable<FieldTripModel>(
      key: _tableKey,
      items: widget.trips,
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
      configKey: FieldTripsTable.CONFIG_KEY,
      initialPinnedColumns: const [FieldTripsTable.COLUMN_TRIP_ID],
      excludeFromPin: const [FieldTripsTable.COLUMN_TRIP_ID],
      excludeFromHide: const [
        FieldTripsTable.COLUMN_TRIP_ID,
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
      searchHintText: AppStrings.FIELD_TRIPS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.map_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    FieldTripModel trip,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case FieldTripsTable.COLUMN_TRIP_ID:
        return _textCell(trip.publicId, isStrong: true);
      case FieldTripsTable.COLUMN_CITY:
        return _textCell(trip.cityName);
      case FieldTripsTable.COLUMN_VILLAGE:
        return _textCell(trip.village);
      case FieldTripsTable.COLUMN_SALES_PERSON:
        return _textCell(trip.salesPersonName);
      case FieldTripsTable.COLUMN_STATUS:
        return FieldTripStatusBadge(trip: trip);
      case FieldTripsTable.COLUMN_EXPECTED_START:
        return _textCell(DateFormatter.instantLabel(trip.expectedStartDateTime));
      case FieldTripsTable.COLUMN_EXPECTED_END:
        return _textCell(DateFormatter.instantLabel(trip.expectedEndDateTime));
      case FieldTripsTable.COLUMN_STARTED_AT:
        return _textCell(DateFormatter.instantLabel(trip.startedDateTime));
      case FieldTripsTable.COLUMN_ENDED_AT:
        return _textCell(DateFormatter.instantLabel(trip.endedDateTime));
      case FieldTripsTable.COLUMN_FARMER_VISITS:
        return Align(
          alignment: Alignment.center,
          child: _textCell('${trip.farmerVisitCount}'),
        );
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Align(
          alignment: Alignment.center,
          child: RowActionsMenu(
            enabled: !widget.isMutating,
            actions: _actionsFor(trip),
          ),
        );
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  /// The status decides the menu: approval is the admin's only lever, and it
  /// disappears entirely once the salesperson has started the trip.
  List<RowAction> _actionsFor(FieldTripModel trip) {
    final bool blocked = widget.isMutating;

    return [
      RowAction(
        label: AppStrings.VIEW_DETAILS,
        icon: Icons.visibility_outlined,
        onSelected: blocked || widget.onView == null
            ? null
            : () => widget.onView!(trip),
      ),
      if (trip.canEdit)
        RowAction(
          label: AppStrings.EDIT,
          icon: Icons.edit_outlined,
          onSelected: blocked || widget.onEdit == null
              ? null
              : () => widget.onEdit!(trip),
        ),
      if (trip.canApprove)
        RowAction(
          label: AppStrings.FIELD_TRIP_APPROVE,
          icon: Icons.verified_outlined,
          tone: RowActionTone.success,
          onSelected: blocked || widget.onApprove == null
              ? null
              : () => widget.onApprove!(trip),
        ),
      if (trip.canUnapprove)
        RowAction(
          label: AppStrings.FIELD_TRIP_UNAPPROVE,
          icon: Icons.undo_rounded,
          tone: RowActionTone.warning,
          onSelected: blocked || widget.onUnapprove == null
              ? null
              : () => widget.onUnapprove!(trip),
        ),
      if (trip.canDelete)
        RowAction(
          label: AppStrings.DELETE,
          icon: Icons.delete_outline_rounded,
          tone: RowActionTone.error,
          onSelected: blocked || widget.onDelete == null
              ? null
              : () => widget.onDelete!(trip),
        ),
    ];
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
