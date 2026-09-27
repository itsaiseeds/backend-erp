import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/dispatch_challan_model.dart';

class ChallanDetailDialog extends StatelessWidget {
  static const String _COLUMN_PRODUCT = 'product';
  static const String _COLUMN_LOT = 'lot_number';
  static const String _COLUMN_WEIGHT = 'packet_weight';
  static const String _COLUMN_PACKETS = 'packets';
  static const String _COLUMN_QUANTITY = 'quantity';
  static const String _COLUMN_TOTAL_WEIGHT = 'total_weight';
  static const String _COLUMN_PRICE = 'price';
  static const String _COLUMN_LINE_TOTAL = 'line_total';

  final DispatchChallanModel challan;

  const ChallanDetailDialog({super.key, required this.challan});

  static Future<void> show(BuildContext context, DispatchChallanModel challan) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ChallanDetailDialog(challan: challan),
    );
  }

  static const List<AppDataColumn> _COLUMNS = [
    AppDataColumn(
      id: _COLUMN_PRODUCT,
      label: AppStrings.COLUMN_PRODUCT,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: _COLUMN_LOT,
      label: AppStrings.COLUMN_LOT_NUMBER,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_WEIGHT,
      label: AppStrings.COLUMN_PACKET_WEIGHT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_PACKETS,
      label: AppStrings.COLUMN_TOTAL_PACKETS,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: _COLUMN_QUANTITY,
      label: AppStrings.COLUMN_QUANTITY,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: _COLUMN_TOTAL_WEIGHT,
      label: AppStrings.COLUMN_TOTAL_WEIGHT,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_PRICE,
      label: AppStrings.COLUMN_SELLING_PRICE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_LINE_TOTAL,
      label: AppStrings.COLUMN_TOTAL_AMOUNT,
      width: AppSizes.tableColumnWidthCompact,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.local_shipping_outlined,
      title: AppStrings.CHALLAN_DETAIL_TITLE,
      subtitle: AppStrings.CHALLAN_DETAIL_SUBTITLE,
      mode: RecordDialogMode.view,
      extraWidth: AppSizes.recordDialogRoomyBump * 2,
      isTall: true,
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (challan.items.isEmpty) {
      return Text(
        AppStrings.CHALLAN_ITEMS_EMPTY,
        style: AppTypography.bodyMedium.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return SizedBox(
      height: AppSizes.challanItemsHeight,
      child: AppDataTable<ChallanItemModel>(
        items: challan.items,
        currentPage: 1,
        totalPages: 0,
        totalItems: challan.items.length,
        columns: _COLUMNS,
        configKey: 'challan-items',
        rowHeight: AppDataTable.standardRowHeight,
        requireColumnSettings: false,
        requireSearchBar: false,
        requirePin: false,
        searchHintText: AppStrings.SEARCH,
        emptyTitle: AppStrings.CHALLAN_ITEMS_EMPTY,
        emptyDescription: AppStrings.TABLE_EMPTY_BODY,
        emptyIcon: Icons.inventory_2_outlined,
        cellBuilder: _buildCell,
      ),
    );
  }

  Widget _buildCell(
    BuildContext context,
    ChallanItemModel item,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case _COLUMN_PRODUCT:
        return _textCell(item.productName, isStrong: true);
      case _COLUMN_LOT:
        return _textCell(item.lotNumber);
      case _COLUMN_WEIGHT:
        return _textCell(item.packetWeight);
      case _COLUMN_PACKETS:
        return _textCell('${item.packets}');
      case _COLUMN_QUANTITY:
        return _textCell('${item.quantity}');
      case _COLUMN_TOTAL_WEIGHT:
        return _textCell(item.totalWeight);
      case _COLUMN_PRICE:
        return _textCell(_effectivePrice(item));
      case _COLUMN_LINE_TOTAL:
        return _textCell(item.lineTotal, isStrong: true);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  // The negotiated price is what the client actually pays when set.
  static String _effectivePrice(ChallanItemModel item) {
    final String negotiated = item.negotiatedSellingPrice.trim();
    if (negotiated.isNotEmpty && negotiated != '0') return negotiated;
    return item.sellingPrice;
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
