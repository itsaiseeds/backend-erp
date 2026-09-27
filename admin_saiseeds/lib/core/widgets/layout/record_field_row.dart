import 'package:flutter/material.dart';
import '../../theme/app_spacing.dart';

class RecordFieldRow extends StatelessWidget {
  final Widget left;
  final Widget? right;

  const RecordFieldRow({super.key, required this.left, this.right});

  @override
  Widget build(BuildContext context) {
    final Widget? trailing = right;

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < AppSizes.detailFieldMinWidth * 2) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              left,
              if (trailing != null) ...[
                const SizedBox(height: AppSpacing.md),
                trailing,
              ],
            ],
          );
        }

        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: left),
            const SizedBox(width: AppSpacing.lg),
            Expanded(child: trailing ?? const SizedBox.shrink()),
          ],
        );
      },
    );
  }
}
