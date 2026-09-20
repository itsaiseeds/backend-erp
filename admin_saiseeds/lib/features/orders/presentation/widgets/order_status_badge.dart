import 'package:flutter/material.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../data/models/order_status.dart';

class OrderStatusBadge extends StatelessWidget {
  final OrderStatus status;

  const OrderStatusBadge({super.key, required this.status});

  static AppBadgeVariant variantOf(OrderStatus status) {
    switch (status) {
      case OrderStatus.booked:
      case OrderStatus.underReview:
        return AppBadgeVariant.warning;
      case OrderStatus.confirmed:
      case OrderStatus.dispatched:
        return AppBadgeVariant.info;
      case OrderStatus.delivered:
        return AppBadgeVariant.success;
      case OrderStatus.rejected:
        return AppBadgeVariant.error;
      case OrderStatus.onHold:
      case OrderStatus.unknown:
        return AppBadgeVariant.neutral;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppBadge(
      label: OrderStatusX.labelOf(status),
      variant: variantOf(status),
    );
  }
}
