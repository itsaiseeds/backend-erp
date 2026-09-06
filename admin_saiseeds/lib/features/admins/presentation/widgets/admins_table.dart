import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/formatters/role_formatter.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/admin_model.dart';

class AdminsTable extends StatefulWidget {
  static const String CONFIG_KEY = 'admins';
  static const String COLUMN_NAME = 'name';
  static const String COLUMN_EMAIL = 'email';
  static const String COLUMN_PHONE_NUMBER = 'phone_number';
  static const String COLUMN_ROLE = 'role';
  static const String COLUMN_CREATED_BY = 'created_by';
  static const String COLUMN_CREATED_AT = 'created_at';

  final List<AdminModel> admins;
  final bool isLoading;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(AdminModel admin)? onEdit;
  final void Function(AdminModel admin)? onDelete;
  final void Function(AdminModel admin)? onView;
  final List<Widget> searchBarActions;
  final String emptyTitle;
  final String emptyDescription;

  const AdminsTable({
    super.key,
    required this.admins,
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
    this.emptyTitle = AppStrings.ADMINS_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.ADMINS_EMPTY_STATE_BODY,
  });

  @override
  State<AdminsTable> createState() => AdminsTableState();
}

class AdminsTableState extends State<AdminsTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: AdminsTable.COLUMN_NAME,
      label: AppStrings.COLUMN_NAME,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: AdminsTable.COLUMN_EMAIL,
      label: AppStrings.COLUMN_EMAIL,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: AdminsTable.COLUMN_PHONE_NUMBER,
      label: AppStrings.COLUMN_PHONE_NUMBER,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AdminsTable.COLUMN_ROLE,
      label: AppStrings.COLUMN_ROLE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: AdminsTable.COLUMN_CREATED_BY,
      label: AppStrings.COLUMN_CREATED_BY,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: AdminsTable.COLUMN_CREATED_AT,
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

  final GlobalKey<AppDataTableState<AdminModel>> _tableKey =
      GlobalKey<AppDataTableState<AdminModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  String _filterLabel(String filter) {
    switch (filter) {
      case AppStrings.FILTER_BY_NAME:
        return AppStrings.COLUMN_NAME;
      case AppStrings.FILTER_BY_PHONE_NUMBER:
        return AppStrings.COLUMN_PHONE_NUMBER;
      case AppStrings.FILTER_BY_ROLE:
        return AppStrings.COLUMN_ROLE;
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
    return AppDataTable<AdminModel>(
      key: _tableKey,
      items: widget.admins,
      isLoading: widget.isLoading,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      rowHeight: AppDataTable.standardRowHeight,
      columns: _COLUMNS,
      configKey: AdminsTable.CONFIG_KEY,
      initialPinnedColumns: const [AdminsTable.COLUMN_NAME],
      excludeFromPin: const [AdminsTable.COLUMN_NAME],
      excludeFromHide: const [
        AdminsTable.COLUMN_NAME,
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
        AppStrings.FILTER_BY_ROLE,
        AppStrings.FILTER_BY_EMAIL,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      getHumanReadableFilterName: _filterLabel,
      getHumanReadableSortName: _sortLabel,
      searchHintText: AppStrings.ADMINS_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.admin_panel_settings_outlined,
      onRowTap: widget.onView,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(BuildContext context, AdminModel admin, AppDataColumn col) {
    switch (col.id) {
      case AdminsTable.COLUMN_NAME:
        return _textCell(admin.name, isStrong: true);
      case AdminsTable.COLUMN_EMAIL:
        return _textCell(admin.email);
      case AdminsTable.COLUMN_PHONE_NUMBER:
        return _textCell(admin.phoneNumber);
      case AdminsTable.COLUMN_ROLE:
        return _textCell(RoleFormatter.label(admin.role));
      case AdminsTable.COLUMN_CREATED_BY:
        return _textCell(admin.createdByName);
      case AdminsTable.COLUMN_CREATED_AT:
        return _textCell(DateFormatter.label(admin.createdAt));
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
                  : () => widget.onView!(admin),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.edit_outlined,
              tooltip: AppStrings.EDIT,
              onPressed: widget.onEdit == null
                  ? null
                  : () => widget.onEdit!(admin),
            ),
            const SizedBox(width: AppSpacing.xs),
            IconActionButton(
              icon: Icons.delete_outline_rounded,
              tooltip: AppStrings.DELETE,
              type: IconActionType.error,
              onPressed: widget.onDelete == null
                  ? null
                  : () => widget.onDelete!(admin),
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
