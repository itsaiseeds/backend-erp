import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/godown_manager_model.dart';

class GodownManagersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'godown_managers';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_EMAIL = 'email';
  static const String COLUMN_PHONE_NUMBER = 'phone_number';
  static const String COLUMN_CREATED_BY = 'created_by';
  static const String COLUMN_CREATED_AT = 'created_at';

  final List<GodownManagerModel> godownManagers;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(GodownManagerModel godownManager)? onDelete;
  final void Function(GodownManagerModel godownManager)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const GodownManagersTable({
    super.key,
    required this.godownManagers,
    required this.isLoading,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.onDelete,
    this.onView,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.GODOWN_MANAGERS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.GODOWN_MANAGERS_EMPTY_STATE_BODY,
  });

  @override
  State<GodownManagersTable> createState() => GodownManagersTableState();
}

class GodownManagersTableState extends State<GodownManagersTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: GodownManagersTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: GodownManagersTable.COLUMN_EMAIL,
      label: AppStrings.COLUMN_EMAIL,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: GodownManagersTable.COLUMN_PHONE_NUMBER,
      label: AppStrings.COLUMN_PHONE_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: GodownManagersTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: GodownManagersTable.COLUMN_CREATED_AT,
      label: AppStrings.COLUMN_CREATED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<GodownManagerModel>> _tableKey =
      GlobalKey<AppDataTableState<GodownManagerModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  String _filterLabel(String filter) {
    switch (filter) {
      case AppStrings.FILTER_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return AppStrings.COLUMN_PHONE_NUMBER;
      case AppStrings.FILTER_BY_EMAIL:
        return AppStrings.COLUMN_EMAIL;
      default:
        return filter;
    }
  }

  String _sortLabel(String sort) {
    switch (sort) {
      case AppStrings.SORT_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.SORT_BY_EMAIL:
        return AppStrings.COLUMN_EMAIL;
      case AppStrings.SORT_BY_CREATED_AT:
        return AppStrings.SORT_LABEL_CREATED_AT;
      default:
        return sort;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<GodownManagerModel>(
      key: _tableKey,
      items: widget.godownManagers,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: GodownManagersTable.CONFIG_KEY,
      initialPinnedColumns: const [GodownManagersTable.COLUMN_NAME],
      excludeFromPin: const [GodownManagersTable.COLUMN_NAME],
      excludeFromHide: const [
        GodownManagersTable.COLUMN_NAME,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: const [
        AppStrings.SORT_BY_NAME,
        AppStrings.SORT_BY_EMAIL,
        AppStrings.SORT_BY_CREATED_AT,
      ],
      filterByOptions: const [
        AppStrings.FILTER_BY_NAME,
        AppStrings.FILTER_BY_PHONE_NUMBER,
        AppStrings.FILTER_BY_EMAIL,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.GODOWN_MANAGERS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.warehouse_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    GodownManagerModel godownManager,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case GodownManagersTable.COLUMN_NAME:
        return _textCell(godownManager.name, isStrong: true);
      case GodownManagersTable.COLUMN_EMAIL:
        return _textCell(godownManager.email);
      case GodownManagersTable.COLUMN_PHONE_NUMBER:
        return _textCell(godownManager.phoneNumber);
      case GodownManagersTable.COLUMN_CREATED_BY:
        return _textCell(godownManager.createdByName);
      case GodownManagersTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(godownManager.createdAt));
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        // An admin's fallback profile is removed with the admin, not from here.
        if (godownManager.isAdmin) return const SizedBox.shrink();
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
                  : () => widget.onDelete!(godownManager),
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
