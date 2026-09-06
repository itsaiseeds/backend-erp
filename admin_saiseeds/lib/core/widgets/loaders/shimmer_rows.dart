import 'package:flutter/material.dart';
import 'shimmer_box.dart';
import '../../theme/app_spacing.dart';

class ShimmerRows extends StatelessWidget {
  final int rowCount;
  final double rowHeight;
  final List<int> columnFlex;

  const ShimmerRows({
    super.key,
    this.rowCount = 6,
    this.rowHeight = AppSpacing.md,
    this.columnFlex = const [1],
  });

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: rowCount,
      separatorBuilder: (context, index) =>
          const SizedBox(height: AppSpacing.md),
      itemBuilder: (context, index) => Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Row(
          children: [
            for (int i = 0; i < columnFlex.length; i++) ...[
              if (i > 0) const SizedBox(width: AppSpacing.md),
              Expanded(
                flex: columnFlex[i],
                child: ShimmerBox(height: rowHeight),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
