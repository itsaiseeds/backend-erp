import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/lab_tester_model.dart';

class LabTestersTable extends StatefulWidget {
  static const String CONFIG_KEY = 'lab_testers';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_EMAIL = 'email';
  static const String COLUMN_PHONE_NUMBER = 'phone_number';
  static const String COLUMN_CREATED_BY = 'created_by';
  static const String COLUMN_CREATED_AT = 'created_at';

  final List<LabTesterModel> labTesters;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(LabTesterModel labTester)? onDelete;
  final void Function(LabTesterModel labTester)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const LabTestersTable({
    super.key,
    required this.labTesters,
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
    this.emptyTitle = AppStrings.LAB_TESTERS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.LAB_TESTERS_EMPTY_STATE_BODY,
  });

  @override
  State<LabTestersTable> createState() => LabTestersTableState();
}

class LabTestersTableState extends State<LabTestersTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: LabTestersTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: LabTestersTable.COLUMN_EMAIL,
      label: AppStrings.COLUMN_EMAIL,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: LabTestersTable.COLUMN_PHONE_NUMBER,
      label: AppStrings.COLUMN_PHONE_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestersTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestersTable.COLUMN_CREATED_AT,
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

  final GlobalKey<AppDataTableState<LabTesterModel>> _tableKey =
      GlobalKey<AppDataTableState<LabTesterModel>>();

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
    return AppDataTable<LabTesterModel>(
      key: _tableKey,
      items: widget.labTesters,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: LabTestersTable.CONFIG_KEY,
      initialPinnedColumns: const [LabTestersTable.COLUMN_NAME],
      excludeFromPin: const [LabTestersTable.COLUMN_NAME],
      excludeFromHide: const [
        LabTestersTable.COLUMN_NAME,
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
      searchHintText: AppStrings.LAB_TESTERS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.biotech_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    LabTesterModel labTester,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case LabTestersTable.COLUMN_NAME:
        return _textCell(labTester.name, isStrong: true);
      case LabTestersTable.COLUMN_EMAIL:
        return _textCell(labTester.email);
      case LabTestersTable.COLUMN_PHONE_NUMBER:
        return _textCell(labTester.phoneNumber);
      case LabTestersTable.COLUMN_CREATED_BY:
        return _textCell(labTester.createdByName);
      case LabTestersTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(labTester.createdAt));
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        // An admin's fallback profile is removed with the admin, not from here.
        if (labTester.isAdmin) return const SizedBox.shrink();
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
                  : () => widget.onDelete!(labTester),
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
