import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/old_sales_person_model.dart';

class OldSalesPeopleTable extends StatefulWidget {
  static const String CONFIG_KEY = 'old-sales-people';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_PHONE_NUMBER = 'phone_number';
  static const String COLUMN_CITY = 'city';
  static const String COLUMN_CLIENT_COUNT = 'client_count';
  static const String COLUMN_STATUS = 'status';

  final List<OldSalesPersonModel> salesPeople;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final List<Widget> searchBarActions;

  const OldSalesPeopleTable({
    super.key,
    required this.salesPeople,
    required this.isLoading,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.searchBarActions = const [],
  });

  @override
  State<OldSalesPeopleTable> createState() => OldSalesPeopleTableState();
}

class OldSalesPeopleTableState extends State<OldSalesPeopleTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: OldSalesPeopleTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: OldSalesPeopleTable.COLUMN_PHONE_NUMBER,
      label: AppStrings.COLUMN_PHONE_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: OldSalesPeopleTable.COLUMN_CITY,
      label: AppStrings.COLUMN_CITY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: OldSalesPeopleTable.COLUMN_CLIENT_COUNT,
      label: AppStrings.COLUMN_CLIENT_COUNT,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    AppDataColumn(
      id: OldSalesPeopleTable.COLUMN_STATUS,
      label: AppStrings.COLUMN_STATUS,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<OldSalesPersonModel>> _tableKey =
      GlobalKey<AppDataTableState<OldSalesPersonModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  @override
  Widget build(BuildContext context) {
    return AppDataTable<OldSalesPersonModel>(
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
      configKey: OldSalesPeopleTable.CONFIG_KEY,
      initialPinnedColumns: const [OldSalesPeopleTable.COLUMN_NAME],
      excludeFromPin: const [OldSalesPeopleTable.COLUMN_NAME],
      excludeFromHide: const [OldSalesPeopleTable.COLUMN_NAME],
      sortByOptions: const [AppStrings.SORT_BY_NAME],
      getHumanReadableSortName: (_) => AppStrings.COLUMN_NAME,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      searchHintText: AppStrings.OLD_SALES_PEOPLE_TABLE_SEARCH_HINT,
      emptyTitle: AppStrings.OLD_SALES_PEOPLE_EMPTY_TITLE,
      emptyDescription: AppStrings.OLD_SALES_PEOPLE_EMPTY_BODY,
      emptyIcon: Icons.person_off_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    OldSalesPersonModel person,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case OldSalesPeopleTable.COLUMN_NAME:
        return _textCell(person.name, isStrong: true);
      case OldSalesPeopleTable.COLUMN_PHONE_NUMBER:
        return _textCell(person.phoneNumber);
      case OldSalesPeopleTable.COLUMN_CITY:
        return _textCell(person.city);
      case OldSalesPeopleTable.COLUMN_CLIENT_COUNT:
        return _textCell('${person.clientCount}');
      case OldSalesPeopleTable.COLUMN_STATUS:
        return const Align(
          alignment: Alignment.center,
          child: AppBadge(
            label: AppStrings.OLD_SALES_PERSON_STATUS_REMOVED,
            variant: AppBadgeVariant.warning,
          ),
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
