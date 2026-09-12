import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/buttons/outlined_action_button.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/client_filter_model.dart';
import '../../data/models/client_model.dart';
import '../../data/models/client_status.dart';

class ClientsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'clients';
  static const String COLUMN_COMPANY = 'company_name';
  static const String COLUMN_PHONE = 'company_phone';
  static const String COLUMN_CONTACT = 'primary_contact';
  static const String COLUMN_ADDRESS = 'primary_address';
  static const String COLUMN_CREATED_BY = 'created_by';
  static const String COLUMN_VERIFIED_BY = 'verified_by';
  static const String COLUMN_REVIEW = 'review';

  final List<ClientModel> clients;
  final bool isLoading;
  final bool isPendingView;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final List<ClientFilterModel> availableFilters;
  final List<ClientSortModel> availableSorts;
  final void Function(ClientModel client)? onView;
  final void Function(ClientModel client)? onEdit;
  final void Function(ClientModel client)? onAccept;
  final void Function(ClientModel client)? onReject;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const ClientsTable({
    super.key,
    required this.clients,
    required this.isLoading,
    required this.isPendingView,
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
    this.onAccept,
    this.onReject,
    this.searchBarActions = const [],
    this.emptyTitle = AppStrings.CLIENTS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.CLIENTS_EMPTY_STATE_BODY,
  });

  @override
  State<ClientsTable> createState() => ClientsTableState();
}

class ClientsTableState extends State<ClientsTable> {
  final GlobalKey<AppDataTableState<ClientModel>> _tableKey =
      GlobalKey<AppDataTableState<ClientModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  List<AppDataColumn> get _columns => [
    const AppDataColumn(
      id: ClientsTable.COLUMN_COMPANY,
      label: AppStrings.COLUMN_COMPANY_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    const AppDataColumn(
      id: ClientsTable.COLUMN_PHONE,
      label: AppStrings.COLUMN_COMPANY_PHONE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    const AppDataColumn(
      id: ClientsTable.COLUMN_CONTACT,
      label: AppStrings.COLUMN_PRIMARY_CONTACT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    const AppDataColumn(
      id: ClientsTable.COLUMN_ADDRESS,
      label: AppStrings.COLUMN_PRIMARY_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
    ),
    const AppDataColumn(
      id: ClientsTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    if (!widget.isPendingView)
      const AppDataColumn(
        id: ClientsTable.COLUMN_VERIFIED_BY,
        label: AppStrings.COLUMN_VERIFIED_BY,
        width: AppSizes.tableColumnWidthMedium,
      ),
    const AppDataColumn(
      id: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      label: AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
    if (widget.isPendingView)
      const AppDataColumn(
        id: ClientsTable.COLUMN_REVIEW,
        label: '',
        width: AppSizes.tableColumnWidthWide,
        isCenter: true,
      ),
  ];

  List<String> get _filterOptions => widget.availableFilters
      .where((filter) => filter.kind != ClientFilterKind.unsupported)
      .where((filter) => filter.key != AppStrings.FILTER_BY_STATUS)
      .where(
        (filter) =>
            !widget.isPendingView ||
            filter.key != AppStrings.FILTER_BY_VERIFIED_BY,
      )
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
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _columns,
      configKey: ClientsTable.CONFIG_KEY,
      initialPinnedColumns: const [ClientsTable.COLUMN_COMPANY],
      excludeFromHide: const [
        ClientsTable.COLUMN_COMPANY,
        ClientsTable.COLUMN_REVIEW,
        AppStrings.TABLE_ACTIONS_COLUMN_LABEL,
      ],
      excludeFromPin: const [
        ClientsTable.COLUMN_COMPANY,
        ClientsTable.COLUMN_REVIEW,
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
      searchHintText: AppStrings.CLIENTS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.storefront_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ClientModel client,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case ClientsTable.COLUMN_COMPANY:
        return _textCell(client.companyName, isStrong: true);
      case ClientsTable.COLUMN_PHONE:
        return _textCell(client.companyPhone);
      case ClientsTable.COLUMN_CONTACT:
        return _textCell(_contactLabel(client));
      case ClientsTable.COLUMN_ADDRESS:
        return _textCell(client.primaryAddress?.formatted ?? '');
      case ClientsTable.COLUMN_CREATED_BY:
        return _textCell(client.createdBy);
      case ClientsTable.COLUMN_VERIFIED_BY:
        return _textCell(client.verifiedBy);
      case ClientsTable.COLUMN_REVIEW:
        return _buildReviewActions(client);
      case AppStrings.TABLE_ACTIONS_COLUMN_LABEL:
        return _buildActions(client);
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

  Widget _buildActions(ClientModel client) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        IconActionButton(
          icon: Icons.visibility_outlined,
          tooltip: AppStrings.VIEW_DETAILS,
          type: IconActionType.primary,
          onPressed: widget.onView == null
              ? null
              : () => widget.onView!(client),
        ),
        const SizedBox(width: AppSpacing.xs),
        IconActionButton(
          icon: Icons.edit_outlined,
          tooltip: AppStrings.EDIT,
          onPressed: widget.onEdit == null
              ? null
              : () => widget.onEdit!(client),
        ),
      ],
    );
  }

  Widget _buildReviewActions(ClientModel client) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        OutlinedActionButton(
          label: AppStrings.CLIENT_ACCEPT,
          icon: Icons.check_circle_outline_rounded,
          onPressed: widget.onAccept == null
              ? null
              : () => widget.onAccept!(client),
        ),
        const SizedBox(width: AppSpacing.sm),
        OutlinedActionButton(
          label: AppStrings.CLIENT_REJECT,
          icon: Icons.cancel_outlined,
          tone: OutlinedActionTone.error,
          onPressed: widget.onReject == null
              ? null
              : () => widget.onReject!(client),
        ),
      ],
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

class ClientStatusBadge extends StatelessWidget {
  final ClientStatus status;

  const ClientStatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    return AppBadge(
      label: ClientStatusX.labelOf(status),
      variant: status == ClientStatus.verified
          ? AppBadgeVariant.success
          : AppBadgeVariant.warning,
    );
  }
}
