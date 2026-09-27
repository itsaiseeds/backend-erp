import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/row_actions_menu.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../data/models/dispatch_challan_model.dart';

class DispatchChallansTable extends StatefulWidget {
  static const String CONFIG_KEY = 'dispatch-challans';
  static const String COLUMN_ORDER_ID = 'order_public_id';
  static const String COLUMN_DISPATCH_ID = 'dispatch_public_id';
  static const String COLUMN_LR = 'lr_number';
  static const String COLUMN_DATE = 'dispatch_date';
  static const String COLUMN_TRANSPORT = 'is_private';
  static const String COLUMN_VEHICLE = 'vehicle_number';
  static const String COLUMN_DRIVER = 'driver';
  static const String COLUMN_FROM_CITY = 'from_city';
  static const String COLUMN_TO_CITY = 'to_city';
  static const String COLUMN_RECEIVER = 'receiver';
  static const String COLUMN_GST = 'gst_number';
  static const String COLUMN_ADDRESS = 'address';
  static const String COLUMN_CONTACT = 'contact_person';
  static const String COLUMN_HSN = 'hsn_code';
  static const String COLUMN_FY = 'financial_year';
  static const String COLUMN_ITEMS = 'item_count';
  static const String COLUMN_PACKETS = 'total_packets';
  static const String COLUMN_AMOUNT = 'total_amount';

  final List<DispatchChallanModel> challans;
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
  final void Function(DispatchChallanModel challan)? onView;
  final void Function(DispatchChallanModel challan)? onPreview;
  final void Function(DispatchChallanModel challan)? onDownload;
  final bool isMutating;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const DispatchChallansTable({
    super.key,
    required this.challans,
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
    this.onPreview,
    this.onDownload,
    this.isMutating = false,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.CHALLANS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.CHALLANS_EMPTY_STATE_BODY,
  });

  @override
  State<DispatchChallansTable> createState() => DispatchChallansTableState();
}

class DispatchChallansTableState extends State<DispatchChallansTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_ORDER_ID,
      label: AppStrings.COLUMN_ORDER_ID,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_DISPATCH_ID,
      label: AppStrings.COLUMN_DISPATCH_ID,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_LR,
      label: AppStrings.COLUMN_LR_NUMBER,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_DATE,
      label: AppStrings.COLUMN_DISPATCH_DATE,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_TRANSPORT,
      label: AppStrings.COLUMN_TRANSPORT_TYPE,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_VEHICLE,
      label: AppStrings.COLUMN_VEHICLE_NUMBER,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_DRIVER,
      label: AppStrings.COLUMN_DRIVER,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_FROM_CITY,
      label: AppStrings.COLUMN_FROM_CITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_TO_CITY,
      label: AppStrings.COLUMN_TO_CITY,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_RECEIVER,
      label: AppStrings.COLUMN_RECEIVER,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_GST,
      label: AppStrings.COLUMN_GST_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_ADDRESS,
      label: AppStrings.COLUMN_RECEIVER_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_CONTACT,
      label: AppStrings.COLUMN_CONTACT_PERSON,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_HSN,
      label: AppStrings.COLUMN_HSN_CODE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_FY,
      label: AppStrings.COLUMN_FINANCIAL_YEAR,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_ITEMS,
      label: AppStrings.COLUMN_ITEM_COUNT,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_PACKETS,
      label: AppStrings.COLUMN_TOTAL_PACKETS,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: DispatchChallansTable.COLUMN_AMOUNT,
      label: AppStrings.COLUMN_TOTAL_AMOUNT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthMedium,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<DispatchChallanModel>> _tableKey =
      GlobalKey<AppDataTableState<DispatchChallanModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  List<String> get _filterOptions {
    final List<String> keys = [AppStrings.FILTER_BY_DATE_RANGE];
    for (final ClientFilterModel filter in widget.availableFilters) {
      if (filter.kind == ClientFilterKind.unsupported) continue;
      if (keys.contains(filter.key)) continue;
      keys.add(filter.key);
    }
    return keys;
  }

  List<String> get _sortOptions => widget.availableSorts.isEmpty
      ? const [AppStrings.SORT_BY_DISPATCH_DATE, AppStrings.SORT_BY_CREATED_AT]
      : widget.availableSorts.map((sort) => sort.key).toList();

  ClientFilterModel? _filterFor(String key) {
    for (final filter in widget.availableFilters) {
      if (filter.key == key) return filter;
    }
    return null;
  }

  bool _isDateRange(String key) => key == AppStrings.FILTER_BY_DATE_RANGE;

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

  String _valueLabelFor(String key, String value) {
    if (_isDateRange(key)) {
      final DateRangeValue parsed = DateRangeValue.parse(value);
      return parsed.isEmpty ? value : parsed.displayValue;
    }
    return _filterFor(key)?.labelForValue(value) ?? value;
  }

  String _filterLabel(String key) {
    if (_isDateRange(key)) return AppStrings.FILTER_LABEL_DATE_RANGE;
    return _filterFor(key)?.displayLabel ?? key;
  }

  String _sortLabel(String key) {
    for (final sort in widget.availableSorts) {
      if (sort.key == key) return sort.displayLabel;
    }
    switch (key) {
      case AppStrings.SORT_BY_DISPATCH_DATE:
        return AppStrings.SORT_LABEL_DISPATCH_DATE;
      case AppStrings.SORT_BY_CREATED_AT:
        return AppStrings.SORT_LABEL_CREATED;
      default:
        return key;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppDataTable<DispatchChallanModel>(
      key: _tableKey,
      items: widget.challans,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: DispatchChallansTable.CONFIG_KEY,
      initialPinnedColumns: const [DispatchChallansTable.COLUMN_ORDER_ID],
      excludeFromPin: const [DispatchChallansTable.COLUMN_ORDER_ID],
      excludeFromHide: const [
        DispatchChallansTable.COLUMN_ORDER_ID,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      sortByOptions: _sortOptions,
      filterByOptions: _filterOptions,
      lockedFilters: const {AppStrings.FILTER_BY_DATE_RANGE},
      filterValueOptions: _valueOptionsFor,
      getFilterValueLabel: _valueLabelFor,
      isDateRangeFilter: _isDateRange,
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.CHALLANS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.local_shipping_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    DispatchChallanModel challan,
    AppDataColumn col,
  ) {
    final ChallanDispatchModel? dispatch = challan.dispatch;

    switch (col.id) {
      case DispatchChallansTable.COLUMN_ORDER_ID:
        return _textCell(challan.orderPublicId, isStrong: true);
      case DispatchChallansTable.COLUMN_DISPATCH_ID:
        return _textCell(challan.dispatchPublicId);
      case DispatchChallansTable.COLUMN_LR:
        return _textCell(dispatch?.lrNumber ?? '');
      case DispatchChallansTable.COLUMN_DATE:
        return _textCell(DateFormatter.dayLabel(dispatch?.dispatchDateTime));
      case DispatchChallansTable.COLUMN_TRANSPORT:
        if (dispatch == null) return _textCell('');
        return AppBadge(
          label: dispatch.isPrivate
              ? AppStrings.TRANSPORT_PRIVATE
              : AppStrings.TRANSPORT_AGENCY,
          variant: dispatch.isPrivate
              ? AppBadgeVariant.info
              : AppBadgeVariant.neutral,
        );
      case DispatchChallansTable.COLUMN_VEHICLE:
        return _textCell(dispatch?.vehicleNumber ?? '');
      case DispatchChallansTable.COLUMN_DRIVER:
        return _textCell(challan.driverSummary);
      case DispatchChallansTable.COLUMN_FROM_CITY:
        return _textCell(dispatch?.fromCity ?? '');
      case DispatchChallansTable.COLUMN_TO_CITY:
        return _textCell(dispatch?.toCity ?? '');
      case DispatchChallansTable.COLUMN_RECEIVER:
        return _textCell(challan.receiverName, isStrong: true);
      case DispatchChallansTable.COLUMN_GST:
        return _textCell(challan.receiverGst);
      case DispatchChallansTable.COLUMN_ADDRESS:
        return _textCell(challan.receiverAddress);
      case DispatchChallansTable.COLUMN_CONTACT:
        return _textCell(challan.contactSummary);
      case DispatchChallansTable.COLUMN_HSN:
        return _textCell(challan.hsnCode);
      case DispatchChallansTable.COLUMN_FY:
        return _textCell(challan.financialYear);
      case DispatchChallansTable.COLUMN_ITEMS:
        return _textCell('${challan.itemCount}');
      case DispatchChallansTable.COLUMN_PACKETS:
        return _textCell('${challan.totalPackets}');
      case DispatchChallansTable.COLUMN_AMOUNT:
        return _textCell(challan.totalAmount, isStrong: true);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return Align(
          alignment: Alignment.center,
          child: RowActionsMenu(
            enabled: !widget.isMutating,
            actions: [
              RowAction(
                label: AppStrings.CHALLAN_VIEW,
                icon: Icons.visibility_outlined,
                onSelected: widget.isMutating || widget.onPreview == null
                    ? null
                    : () => widget.onPreview!(challan),
              ),
              RowAction(
                label: AppStrings.DOWNLOAD,
                icon: Icons.download_outlined,
                onSelected:
                    widget.isMutating || widget.onDownload == null
                    ? null
                    : () => widget.onDownload!(challan),
              ),
            ],
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
