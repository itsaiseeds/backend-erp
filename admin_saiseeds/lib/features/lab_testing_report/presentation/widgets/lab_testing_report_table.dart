import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/lab_testing_report_model.dart';

class LabTestingReportTable extends StatefulWidget {
  static const String CONFIG_KEY = 'lab-testing-report';
  static const String COLUMN_PUBLIC_ID = 'public_id';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_LOT_NO = 'lot_no';
  static const String COLUMN_PARTY = 'party';
  static const String COLUMN_RESULT = 'result';
  static const String COLUMN_GENETICAL_IMPURITY = 'genetical_impurity';
  static const String COLUMN_GROW_OUT_TEST = 'grow_out_test';
  static const String COLUMN_TESTED_BY = 'tested_by';
  static const String COLUMN_TESTED_AT = 'tested_at';

  final List<LabTestingReportModel> tests;
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
  final void Function(LabTestingReportModel test)? onView;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const LabTestingReportTable({
    super.key,
    required this.tests,
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
    this.emptyTitle = AppStrings.LAB_TESTING_REPORT_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.LAB_TESTING_REPORT_EMPTY_STATE_BODY,
  });

  @override
  State<LabTestingReportTable> createState() => LabTestingReportTableState();
}

class LabTestingReportTableState extends State<LabTestingReportTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_PUBLIC_ID,
      label: AppStrings.COLUMN_REFERENCE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_LOT_NO,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_LOT_NO,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_PARTY,
      label: AppStrings.COLUMN_PARTY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_RESULT,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_RESULT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_GENETICAL_IMPURITY,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_GENETICAL_IMPURITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_GROW_OUT_TEST,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_GROW_OUT_TEST,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_TESTED_BY,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_TESTED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: LabTestingReportTable.COLUMN_TESTED_AT,
      label: AppStrings.LAB_TESTING_REPORT_COLUMN_TESTED_AT,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

  final GlobalKey<AppDataTableState<LabTestingReportModel>> _tableKey =
      GlobalKey<AppDataTableState<LabTestingReportModel>>();

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
    return AppDataTable<LabTestingReportModel>(
      key: _tableKey,
      items: widget.tests,
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
      configKey: LabTestingReportTable.CONFIG_KEY,
      initialPinnedColumns: const [LabTestingReportTable.COLUMN_PUBLIC_ID],
      excludeFromPin: const [LabTestingReportTable.COLUMN_PUBLIC_ID],
      excludeFromHide: const [LabTestingReportTable.COLUMN_PUBLIC_ID],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.LAB_TESTING_REPORT_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.biotech_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    LabTestingReportModel test,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case LabTestingReportTable.COLUMN_PUBLIC_ID:
        return _textCell(test.publicId, isStrong: true);
      case LabTestingReportTable.COLUMN_PRODUCT:
        return _textCell(test.productName);
      case LabTestingReportTable.COLUMN_LOT_NO:
        return _textCell(test.lotNo);
      case LabTestingReportTable.COLUMN_PARTY:
        return _textCell(test.partyName);
      case LabTestingReportTable.COLUMN_RESULT:
        return _resultBadge(test.result);
      case LabTestingReportTable.COLUMN_GENETICAL_IMPURITY:
        return _textCell(_percent(test.geneticalImpurity));
      case LabTestingReportTable.COLUMN_GROW_OUT_TEST:
        return _textCell(_percent(test.growOutTest));
      case LabTestingReportTable.COLUMN_TESTED_BY:
        return _textCell(test.testedByName);
      case LabTestingReportTable.COLUMN_TESTED_AT:
        return _textCell(DateFormatter.label(test.testedAt));
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  Widget _resultBadge(String result) {
    final String trimmed = result.trim();
    if (trimmed.isEmpty) {
      return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
    final bool isPass = trimmed.toLowerCase() == 'pass';
    return AppBadge(
      label: trimmed,
      variant: isPass ? AppBadgeVariant.success : AppBadgeVariant.error,
    );
  }

  String _percent(String value) {
    final String trimmed = value.trim();
    return trimmed.isEmpty ? '' : '$trimmed%';
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
