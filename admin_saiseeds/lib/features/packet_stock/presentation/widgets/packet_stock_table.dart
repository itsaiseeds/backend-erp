import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/inputs/stock_count_field.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/packet_stock_line_model.dart';

class PacketStockTable extends StatefulWidget {
  static const String CONFIG_KEY = 'packet-stock';
  static const String COLUMN_PRODUCT = 'product';
  static const String COLUMN_PACKET_WEIGHT = 'packet_weight';
  static const String COLUMN_ON_HAND = 'on_hand';
  static const String COLUMN_RESERVED = 'reserved';
  static const String COLUMN_CONSUMED = 'consumed';
  static const String COLUMN_AVAILABLE = 'available';
  static const String COLUMN_COUNTED = 'counted';

  final List<PacketStockLineModel> lines;
  final Map<String, int> draftCounts;
  final bool isLoading;
  final bool isSubmitting;
  final int currentPage;
  final int totalPages;
  final int totalItems;
  final TableFetchCallback onFetchData;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final void Function(String poolKey, int? count) onCountChanged;
  final List<Widget> searchBarActions;
  final Widget? searchBarTrailing;
  final String emptyTitle;
  final String emptyDescription;

  const PacketStockTable({
    super.key,
    required this.lines,
    required this.draftCounts,
    required this.isLoading,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.onFetchData,
    required this.onCountChanged,
    this.isSubmitting = false,
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.searchBarActions = const [],
    this.searchBarTrailing,
    this.emptyTitle = AppStrings.PACKET_STOCK_EMPTY_STATE_TITLE,
    this.emptyDescription = AppStrings.PACKET_STOCK_EMPTY_STATE_BODY,
  });

  @override
  State<PacketStockTable> createState() => PacketStockTableState();
}

class PacketStockTableState extends State<PacketStockTable> {
  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: PacketStockTable.COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_PACKET_WEIGHT,
      label: AppStrings.COLUMN_PACKET_WEIGHT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_ON_HAND,
      label: AppStrings.COLUMN_STOCK_ON_HAND,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_RESERVED,
      label: AppStrings.COLUMN_STOCK_RESERVED,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_CONSUMED,
      label: AppStrings.COLUMN_STOCK_CONSUMED,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_AVAILABLE,
      label: AppStrings.COLUMN_STOCK_AVAILABLE,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: PacketStockTable.COLUMN_COUNTED,
      label: AppStrings.COLUMN_STOCK_COUNTED,
      width: AppSizes.tableColumnWidthCompact,
      isCenter: true,
    ),
  ];

  final GlobalKey<AppDataTableState<PacketStockLineModel>> _tableKey =
      GlobalKey<AppDataTableState<PacketStockLineModel>>();

  void showColumnSettings() => _tableKey.currentState?.showColumnSettings();

  @override
  Widget build(BuildContext context) {
    return AppDataTable<PacketStockLineModel>(
      key: _tableKey,
      items: widget.lines,
      isLoading: widget.isLoading,
      isOperationInProgress: widget.isSubmitting,
      currentPage: widget.currentPage,
      totalPages: widget.totalPages,
      totalItems: widget.totalItems,
      onFetchData: widget.onFetchData,
      searchBarActions: widget.searchBarActions,
      searchBarTrailing: widget.searchBarTrailing,
      rowHeight: AppSizes.tableRowHeight,
      columns: _COLUMNS,
      configKey: PacketStockTable.CONFIG_KEY,
      initialPinnedColumns: const [PacketStockTable.COLUMN_PRODUCT],
      excludeFromPin: const [PacketStockTable.COLUMN_PRODUCT],
      excludeFromHide: const [
        PacketStockTable.COLUMN_PRODUCT,
        PacketStockTable.COLUMN_COUNTED,
      ],
      sortByOptions: const [
        AppStrings.SORT_BY_PRODUCT,
        AppStrings.SORT_BY_PACKET_WEIGHT,
      ],
      currentSortBy: widget.currentSortBy,
      currentSortOrder: widget.currentSortOrder,
      currentFilters: widget.currentFilters,
      searchHintText: AppStrings.PACKET_STOCK_TABLE_SEARCH_HINT,
      emptyTitle: widget.emptyTitle,
      emptyDescription: widget.emptyDescription,
      emptyIcon: Icons.category_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    PacketStockLineModel line,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case PacketStockTable.COLUMN_PRODUCT:
        return _textCell(line.productName, isStrong: true);
      case PacketStockTable.COLUMN_PACKET_WEIGHT:
        return _textCell(line.packetWeight);
      case PacketStockTable.COLUMN_ON_HAND:
        return _textCell('${line.onHand}');
      case PacketStockTable.COLUMN_RESERVED:
        return _textCell('${line.reserved}');
      case PacketStockTable.COLUMN_CONSUMED:
        return _textCell('${line.consumed}');
      case PacketStockTable.COLUMN_AVAILABLE:
        return _textCell('${line.available}', isStrong: true);
      case PacketStockTable.COLUMN_COUNTED:
        return SizedBox.expand(
          child: StockCountField(
            value: widget.draftCounts[line.poolKey],
            enabled: !widget.isSubmitting,
            onChanged: (count) => widget.onCountChanged(line.poolKey, count),
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
