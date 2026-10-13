import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../custom_orders/data/models/custom_order_model.dart';
import '../../../orders/presentation/widgets/order_status_badge.dart';

/// Read-only walk-through of a booked rejected-lot order. There is no edit
/// path for this order kind (booking is its own dispatch, so nothing is left
/// to confirm or amend), so this only steps through what the order already
/// is -- summary, the lots it was booked against, and what delivery details
/// the API actually returns. Driver/vehicle details live in a private
/// dispatch record the client payload never carries, so there is no separate
/// shipment step for them.
class RejectedLotOrderDetailDialog extends StatefulWidget {
  final CustomOrderModel order;

  const RejectedLotOrderDetailDialog({super.key, required this.order});

  static Future<void> show(
    BuildContext context, {
    required CustomOrderModel order,
  }) {
    return showDialog<void>(
      context: context,
      builder: (_) => RejectedLotOrderDetailDialog(order: order),
    );
  }

  @override
  State<RejectedLotOrderDetailDialog> createState() =>
      _RejectedLotOrderDetailDialogState();
}

class _RejectedLotOrderDetailDialogState
    extends State<RejectedLotOrderDetailDialog> {
  static const List<IconData> _ICONS = [
    Icons.summarize_outlined,
    Icons.inventory_2_outlined,
    Icons.local_shipping_outlined,
  ];

  static const List<String> _STEPS = [
    AppStrings.ORDER_STEP_SUMMARY,
    AppStrings.REJECTED_LOT_ORDER_SUMMARY_LOTS,
    AppStrings.REJECTED_LOT_ORDER_STEP_SHIPMENT,
  ];

  int _stepIndex = 0;

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  CustomOrderModel get _order => widget.order;

  void _goTo(int index) =>
      setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.remove_shopping_cart_outlined,
      title: _order.publicId,
      subtitle:
          '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
          '${AppStrings.LABEL_SEPARATOR} ${_STEPS[_stepIndex]}',
      mode: RecordDialogMode.edit,
      badge: Padding(
        padding: const EdgeInsets.only(left: AppSpacing.sm),
        child: OrderStatusBadge(status: _order.statusValue),
      ),
      extraHeight: AppSizes.recordDialogRoomyBump,
      onCancelEdit: _isFirstStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CLOSE : AppStrings.STEP_BACK,
      onSubmit: _isLastStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex + 1),
      submitLabel: _isLastStep ? AppStrings.CLOSE : AppStrings.STEP_NEXT,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          SectionTitle(
            title: _STEPS[_stepIndex],
            icon: _ICONS[_stepIndex],
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _buildStep(),
        ],
      ),
    );
  }

  Widget _buildStep() {
    switch (_stepIndex) {
      case 1:
        return _buildLots();
      case 2:
        return _buildShipment();
      default:
        return _buildSummary();
    }
  }

  Widget _buildSummary() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _DetailRow(label: AppStrings.COLUMN_ORDER_CLIENT, value: _order.clientName),
        _DetailRow(
          label: AppStrings.FIELD_FARMER,
          value: _order.bookedFor?.displayLabel ?? '',
        ),
        _DetailRow(
          label: AppStrings.COLUMN_ORDER_AMOUNT,
          value: CurrencyFormatter.rupees(_order.totalAmountValue ?? 0),
        ),
        _DetailRow(
          label: AppStrings.COLUMN_CUSTOM_ORDER_ITEMS,
          value: '${_order.itemCount}',
        ),
        if (_order.specialComments.trim().isNotEmpty)
          _DetailRow(
            label: AppStrings.FIELD_SPECIAL_COMMENTS,
            value: _order.specialComments,
          ),
      ],
    );
  }

  Widget _buildLots() {
    if (_order.items.isEmpty) {
      return Text(
        AppStrings.DISPATCH_ITEMS_EMPTY,
        style: AppTypography.bodyMedium.copyWith(color: AppColors.TEXT_SECONDARY),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final CustomOrderItemModel item in _order.items)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.md),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(item.productName, style: AppTypography.labelStrong),
                const SizedBox(height: AppSpacing.xxs),
                if (item.lot != null)
                  Text(
                    '${item.lot!.lotNo} - ${item.lot!.farmerName}',
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                const SizedBox(height: AppSpacing.xs),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${item.quantityKg} kg @ '
                        '${CurrencyFormatter.rupees(item.priceValue ?? 0)}',
                        style: AppTypography.bodySmall,
                      ),
                    ),
                    Text(
                      CurrencyFormatter.rupees(item.lineTotalValue),
                      style: AppTypography.labelStrong,
                    ),
                  ],
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildShipment() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _DetailRow(
          label: AppStrings.COLUMN_CUSTOM_ORDER_CITY,
          value: _order.cityName,
        ),
        _DetailRow(
          label: AppStrings.COLUMN_CUSTOM_ORDER_EXPECTED,
          value: DateFormatter.dayLabel(_order.expectedDeliveryDateTime),
        ),
        _DetailRow(
          label: AppStrings.COLUMN_ORDER_PLACED,
          value: DateFormatter.instantLabel(_order.createdAtDateTime),
        ),
        _DetailRow(label: AppStrings.COLUMN_ORDER_SALES_PERSON, value: _order.createdBy),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Text(
              value.trim().isEmpty ? AppStrings.TABLE_VALUE_UNAVAILABLE : value,
              textAlign: TextAlign.right,
              style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}
