import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/models/client_filter_model.dart';
import '../../../clients/data/models/client_model.dart';

class TransferClientTable extends StatefulWidget {
  static const String CONFIG_KEY = 'transfer-client';
  static const String COLUMN_COMPANY = 'company_name';
  static const String COLUMN_PHONE = 'company_phone';
  static const String COLUMN_CONTACT = 'primary_contact';
  static const String COLUMN_ADDRESS = 'primary_address';
  static const String COLUMN_CREATED_BY = 'created_by';

  final List<ClientModel> clients;
  final bool isLoading;
  final bool hasSource;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final bool hasMore;
  final VoidCallback? onLoadMore;
  final void Function(Map<String, String> selection) onSelectionChanged;
  final Widget searchBarTrailing;
  final List<Widget> searchBarActions;

  const TransferClientTable({
    super.key,
    required this.clients,
    required this.isLoading,
    required this.hasSource,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.availableFilters = const [],
    this.availableSorts = const [],
    this.hasMore = false,
    this.onLoadMore,
    required this.onSelectionChanged,
    required this.searchBarTrailing,
    this.searchBarActions = const [],
  });

  @override
  State<TransferClientTable> createState() => TransferClientTableState();
}

class TransferClientTableState extends State<TransferClientTable> {
  final GlobalKey<AppDataTableState<ClientModel>> _tableKey =
      GlobalKey<AppDataTableState<ClientModel>>();

  void clearSelection() => _tableKey.currentState?.clearSelection();

  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: TransferClientTable.COLUMN_COMPANY,
      label: AppStrings.COLUMN_COMPANY_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: TransferClientTable.COLUMN_PHONE,
      label: AppStrings.COLUMN_COMPANY_PHONE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: TransferClientTable.COLUMN_CONTACT,
      label: AppStrings.COLUMN_PRIMARY_CONTACT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: TransferClientTable.COLUMN_ADDRESS,
      label: AppStrings.COLUMN_PRIMARY_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: TransferClientTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

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
    return AppDataTable<ClientModel>(
      key: _tableKey,
      items: widget.clients,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      isInfiniteScroll: true,
      hasMore: widget.hasMore,
      onLoadMore: widget.onLoadMore,
      searchBarTrailing: widget.searchBarTrailing,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: TransferClientTable.CONFIG_KEY,
      initialPinnedColumns: const [TransferClientTable.COLUMN_COMPANY],
      excludeFromPin: const [TransferClientTable.COLUMN_COMPANY],
      excludeFromHide: const [TransferClientTable.COLUMN_COMPANY],
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
      searchHintText: AppStrings.TRANSFER_CLIENT_TABLE_SEARCH_HINT,
      emptyTitle: widget.hasSource
          ? AppStrings.TRANSFER_CLIENT_EMPTY_TITLE
          : AppStrings.TRANSFER_CLIENT_EMPTY_TITLE_NO_SELECTION,
      emptyDescription: widget.hasSource
          ? AppStrings.TRANSFER_CLIENT_EMPTY_BODY
          : AppStrings.TRANSFER_CLIENT_EMPTY_BODY_NO_SELECTION,
      emptyIcon: widget.hasSource
          ? Icons.storefront_outlined
          : Icons.person_search_outlined,
      requireSelects: true,
      selectionIdExtractor: (client) => client.publicId,
      selectionLabelExtractor: (client) => client.companyName,
      onSelectionChanged: widget.onSelectionChanged,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ClientModel client,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case TransferClientTable.COLUMN_COMPANY:
        return _textCell(client.companyName, isStrong: true);
      case TransferClientTable.COLUMN_PHONE:
        return _textCell(client.companyPhone);
      case TransferClientTable.COLUMN_CONTACT:
        return _textCell(_contactLabel(client));
      case TransferClientTable.COLUMN_ADDRESS:
        return _textCell(client.primaryAddress?.formatted ?? '');
      case TransferClientTable.COLUMN_CREATED_BY:
        return _textCell(client.createdBy);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  static String _contactLabel(ClientModel client) {
    final contact = client.primaryContact;
    if (contact == null) return '';
    return [
      contact.name,
      contact.phoneNumber,
    ].where((part) => part.trim().isNotEmpty).join(' · ');
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
