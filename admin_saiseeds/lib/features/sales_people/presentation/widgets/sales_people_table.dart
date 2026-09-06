import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/sales_person_model.dart';

class SalesPeopleTable extends StatefulWidget {
  static const String CONFIG_KEY = 'sales_people';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_EMAIL = 'email';
  static const String COLUMN_PHONE_NUMBER = 'phone_number';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_CREATED_BY = 'created_by';
  static const String COLUMN_CREATED_AT = 'created_at';

  final List<SalesPersonModel> salesPeople;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(SalesPersonModel salesPerson)? onEdit;
  final void Function(SalesPersonModel salesPerson)? onDelete;
  final void Function(SalesPersonModel salesPerson)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const SalesPeopleTable({
    super.key,
    required this.salesPeople,
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
    this.emptyTitle = AppStrings.SALES_PEOPLE_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.SALES_PEOPLE_EMPTY_STATE_BODY,
  });

  @override
  State<SalesPeopleTable> createState() => SalesPeopleTableState();
}

class SalesPeopleTableState extends State<SalesPeopleTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_EMAIL,
      label: AppStrings.COLUMN_EMAIL,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_PHONE_NUMBER,
      label: AppStrings.COLUMN_PHONE_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: SalesPeopleTable.COLUMN_CREATED_AT,
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

  final GlobalKey<AppDataTableState<SalesPersonModel>> _tableKey =
      GlobalKey<AppDataTableState<SalesPersonModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  String _filterLabel(String filter) {
    switch (filter) {
      case AppStrings.FILTER_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return AppStrings.COLUMN_PHONE_NUMBER;
      case AppStrings.FILTER_BY_EMAIL:
        return AppStrings.COLUMN_EMAIL;
      case AppStrings.FILTER_BY_CITY:
        return AppStrings.COLUMN_CITY;
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
    return AppDataTable<SalesPersonModel>(
      key: _tableKey,
      items: widget.salesPeople,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: SalesPeopleTable.CONFIG_KEY,
      initialPinnedColumns: const [SalesPeopleTable.COLUMN_NAME],
      excludeFromPin: const [SalesPeopleTable.COLUMN_NAME],
      excludeFromHide: const [
        SalesPeopleTable.COLUMN_NAME,
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
        AppStrings.FILTER_BY_CITY,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.SALES_PEOPLE_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.groups_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    SalesPersonModel salesPerson,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case SalesPeopleTable.COLUMN_NAME:
        return _textCell(salesPerson.name, isStrong: true);
      case SalesPeopleTable.COLUMN_EMAIL:
        return _textCell(salesPerson.email);
      case SalesPeopleTable.COLUMN_PHONE_NUMBER:
        return _textCell(salesPerson.phoneNumber);
      case SalesPeopleTable.COLUMN_CITY:
        return _textCell(salesPerson.cityName);
      case SalesPeopleTable.COLUMN_CREATED_BY:
        return _textCell(salesPerson.createdByName);
      case SalesPeopleTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(salesPerson.createdAt));
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            IconActionButton(
              icon: Icons.qr_code_2_rounded,
              tooltip: AppStrings.VIEW_DETAILS,
              type: IconActionType.primary,
              onPressed: widget.onView == null
                  ? null
                  : () => widget.onView!(salesPerson),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.edit_outlined,
              tooltip: AppStrings.EDIT,
              onPressed: widget.onEdit == null
                  ? null
                  : () => widget.onEdit!(salesPerson),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.delete_outline_rounded,
              tooltip: AppStrings.DELETE,
              type: IconActionType.error,
              onPressed: widget.onDelete == null
                  ? null
                  : () => widget.onDelete!(salesPerson),
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
