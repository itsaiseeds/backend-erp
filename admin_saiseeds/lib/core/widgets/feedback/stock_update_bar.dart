import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../buttons/primary_button.dart';

class StockUpdateBar extends StatelessWidget {
  final int pendingCount;
  final bool isSubmitting;
  final VoidCallback? onUpdate;

  const StockUpdateBar({
    super.key,
    required this.pendingCount,
    required this.onUpdate,
    this.isSubmitting = false,
  });

  String get _label => pendingCount > 0
      ? '${AppStrings.STOCK_UPDATE_ACTION} ($pendingCount)'
      : AppStrings.STOCK_UPDATE_ACTION;

  @override
  Widget build(BuildContext context) {
    return PrimaryButton(
      label: _label,
      icon: Icons.inventory_rounded,
      isLoading: isSubmitting,
      onPressed: isSubmitting ? null : onUpdate,
    );
  }
}
