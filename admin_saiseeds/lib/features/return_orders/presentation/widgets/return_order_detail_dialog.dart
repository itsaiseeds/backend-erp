import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/return_order_model.dart';
import '../../data/models/return_order_status.dart';
import 'return_order_status_badge.dart';

/// Read-only view of one return.
///
/// Editing and the lifecycle verbs live in the table's row actions, so this
/// dialog only has to answer "what is in this return and where did it get to".
class ReturnOrderDetailDialog extends StatelessWidget {
  final ReturnOrderModel returnOrder;

  const ReturnOrderDetailDialog({super.key, required this.returnOrder});

  static Future<void> show(BuildContext context, ReturnOrderModel returnOrder) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ReturnOrderDetailDialog(returnOrder: returnOrder),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ReturnOrderModel order = returnOrder;

    return AppRecordDialog(
      icon: Icons.assignment_return_outlined,
      title: AppStrings.RETURN_ORDER_DETAILS_TITLE,
      subtitle: order.publicId,
      mode: RecordDialogMode.view,
      showFooterInViewMode: true,
      isTall: true,
      badge: ReturnOrderStatusBadge(status: order.status),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            DetailFieldGrid(
              fields: [
                DetailField(
                  label: AppStrings.COLUMN_RETURN_CLIENT,
                  value: order.client.companyName,
                ),
                DetailField(
                  label: AppStrings.COLUMN_RETURN_ORDER,
                  value: order.order.publicId,
                ),
                DetailField(
                  label: AppStrings.RETURN_ORDER_EDIT_DATE,
                  value: DateFormatter.label(_isoDate(order.returnDate)),
                ),
                DetailField(
                  label: AppStrings.COLUMN_RETURN_RAISED_BY,
                  value: order.createdByName,
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.lg),
            SectionTitle(
              title: _itemsLabel(order),
              icon: Icons.inventory_2_outlined,
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.md),
            if (order.items.isEmpty)
              Text(
                AppStrings.TABLE_VALUE_UNAVAILABLE,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              )
            else
              ...order.items.map(_ItemRow.new),
            const SizedBox(height: AppSpacing.md),
            const AppHairline(),
            const SizedBox(height: AppSpacing.md),
            _Totals(returnOrder: order),
            if (_decisionOf(order) != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _decisionOf(order)!,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
            if (_hasInwardLots(order)) ...[
              const SizedBox(height: AppSpacing.lg),
              SectionTitle(
                title: AppStrings.RETURN_ORDER_INWARD_LOTS,
                icon: Icons.warehouse_outlined,
                hasRule: true,
              ),
              const SizedBox(height: AppSpacing.md),
              _LotList(
                label: AppStrings.RETURN_ORDER_INWARD_RAW_TITLE,
                lots: order.inwardRawMaterials,
              ),
              _LotList(
                label: AppStrings.RETURN_ORDER_INWARD_OTHER_TITLE,
                lots: order.inwardOtherMaterials,
              ),
              const SizedBox(height: AppSpacing.sm),
              Text(
                order.includeInOtherRawMaterials == true
                    ? AppStrings.RETURN_ORDER_MATERIALS_BOOKED_YES
                    : AppStrings.RETURN_ORDER_MATERIALS_BOOKED_NO,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  static bool _hasInwardLots(ReturnOrderModel order) =>
      order.inwardRawMaterials.isNotEmpty ||
      order.inwardOtherMaterials.isNotEmpty;

  static String _itemsLabel(ReturnOrderModel order) {
    final int count = order.items.length;
    return count == 1
        ? AppStrings.RETURN_ORDER_ITEMS_TITLE_ONE
        : AppStrings.RETURN_ORDER_ITEMS_TITLE_MANY.replaceAll('%s', '$count');
  }

  /// Who last acted on the return, and what they decided.
  static String? _decisionOf(ReturnOrderModel order) {
    switch (order.status) {
      case ReturnOrderStatus.accepted:
        return AppStrings.RETURN_ORDER_ACCEPTED_BY.replaceAll(
          '%s',
          order.verifiedByName,
        );
      case ReturnOrderStatus.rejected:
        return AppStrings.RETURN_ORDER_REJECTED_BY.replaceAll(
          '%s',
          order.rejectedByName,
        );
      case ReturnOrderStatus.pending:
      case ReturnOrderStatus.unknown:
        return null;
    }
  }

  static String _isoDate(DateTime? value) {
    if (value == null) return '';
    final String month = value.month.toString().padLeft(2, '0');
    final String day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }
}

class _ItemRow extends StatelessWidget {
  final ReturnOrderItemModel item;

  const _ItemRow(this.item);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(item.product.name, style: AppTypography.bodyMedium),
                Text(
                  AppStrings.RETURN_ORDER_ITEM_PACKET_SUMMARY
                      .replaceAll('%s', item.packetWeightLabel)
                      .replaceAll('%t', '${item.packets}'),
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                CurrencyFormatter.rupees(item.pricePerPacket),
                style: AppTypography.bodyMedium,
              ),
              Text(
                CurrencyFormatter.rupees(item.lineTotal),
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _Totals extends StatelessWidget {
  final ReturnOrderModel returnOrder;

  const _Totals({required this.returnOrder});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_PACKETS,
            value: '${returnOrder.totalPackets}',
          ),
        ),
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_KG,
            value: '${_trim(returnOrder.totalKg)} Kg',
          ),
        ),
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_AMOUNT,
            value: CurrencyFormatter.rupees(returnOrder.totalAmount),
          ),
        ),
      ],
    );
  }

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}

class _Total extends StatelessWidget {
  final String label;
  final String value;

  const _Total({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        Text(value, style: AppTypography.titleMedium),
      ],
    );
  }
}

class _LotList extends StatelessWidget {
  final String label;
  final List<String> lots;

  const _LotList({required this.label, required this.lots});

  @override
  Widget build(BuildContext context) {
    if (lots.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
          Text(lots.join(', '), style: AppTypography.bodyMedium),
        ],
      ),
    );
  }
}
