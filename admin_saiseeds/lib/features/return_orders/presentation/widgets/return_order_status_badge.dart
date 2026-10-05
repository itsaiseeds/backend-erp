import 'package:flutter/material.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../data/models/return_order_status.dart';

class ReturnOrderStatusBadge extends StatelessWidget {
  final ReturnOrderStatus status;

  const ReturnOrderStatusBadge({super.key, required this.status});

  static AppBadgeVariant variantOf(ReturnOrderStatus status) {
    switch (status) {
      case ReturnOrderStatus.pending:
        return AppBadgeVariant.warning;
      case ReturnOrderStatus.accepted:
        return AppBadgeVariant.success;
      case ReturnOrderStatus.rejected:
        return AppBadgeVariant.error;
      case ReturnOrderStatus.unknown:
        return AppBadgeVariant.neutral;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppBadge(
      label: ReturnOrderStatusX.labelOf(status),
      variant: variantOf(status),
    );
  }
}
