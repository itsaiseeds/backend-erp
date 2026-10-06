import 'package:flutter/material.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../data/models/return_order_model.dart';
import '../../data/return_orders_repository.dart';
import 'return_order_detail_dialog.dart';

/// The edit entry point for a return.
///
/// Editing lives inside [ReturnOrderDetailDialog] so that the header pencil
/// and the table's Edit action open the very same three-step dialog. This
/// wrapper only pins it to edit mode and keeps the old call site's signature.
class ReturnOrderEditDialog extends StatelessWidget {
  final ReturnOrderModel returnOrder;
  final ReturnOrdersRepository repository;

  const ReturnOrderEditDialog({
    super.key,
    required this.returnOrder,
    required this.repository,
  });

  static Future<bool> show(
    BuildContext context, {
    required ReturnOrderModel returnOrder,
    required ReturnOrdersRepository repository,
  }) {
    return ReturnOrderDetailDialog.show(
      context,
      returnOrder,
      repository: repository,
      initialMode: RecordDialogMode.edit,
    );
  }

  @override
  Widget build(BuildContext context) {
    return ReturnOrderDetailDialog(
      returnOrder: returnOrder,
      repository: repository,
      initialMode: RecordDialogMode.edit,
    );
  }
}
