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
import '../../data/models/party_model.dart';

class PartiesTable extends StatefulWidget {
  static const String CONFIG_KEY = 'parties';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_CONTACT = 'contact_number';

  final List<PartyModel> parties;
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
  final void Function(PartyModel party)? onDelete;
  final void Function(PartyModel party)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const PartiesTable({
    super.key,
    required this.parties,
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
    this.onView,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.PARTIES_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PARTIES_EMPTY_STATE_BODY,
  });

  @override
  State<PartiesTable> createState() => PartiesTableState();
}

class PartiesTableState extends State<PartiesTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: PartiesTable.COLUMN_NAME,
      label: AppStrings.COLUMN_PARTY_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: PartiesTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CITY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: PartiesTable.COLUMN_CONTACT,
      label: AppStrings.COLUMN_PARTY_CONTACT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<PartyModel>> _tableKey =
      GlobalKey<AppDataTableState<PartyModel>>();

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
    return AppDataTable<PartyModel>(
      key: _tableKey,
      items: widget.parties,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: PartiesTable.CONFIG_KEY,
      initialPinnedColumns: const [PartiesTable.COLUMN_NAME],
      excludeFromPin: const [PartiesTable.COLUMN_NAME],
      excludeFromHide: const [
        PartiesTable.COLUMN_NAME,
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
      searchHintText: AppStrings.PARTIES_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.handshake_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(BuildContext context, PartyModel party, AppDataColumn col) {
    switch (col.id) {
      case PartiesTable.COLUMN_NAME:
        return _textCell(party.name, isStrong: true);
      case PartiesTable.COLUMN_CITY:
        return _textCell(party.cityName);
      case PartiesTable.COLUMN_CONTACT:
        return _textCell(party.contactNumber);
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
                  : () => widget.onDelete!(party),
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
