import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppTableHeader extends StatelessWidget {
  final List<AppTableHeaderCell> cells;

  const AppTableHeader({super.key, required this.cells});

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.TABLE_HEADER_BG,
        border: Border(bottom: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: _buildCells(),
        ),
      ),
    );
  }

  List<Widget> _buildCells() {
    final List<Widget> children = [];
    for (int i = 0; i < cells.length; i++) {
      children.add(cells[i]);
      if (i < cells.length - 1) {
        children.add(
          const VerticalDivider(
            width: AppSizes.borderThin,
            thickness: AppSizes.borderThin,
            color: AppColors.TABLE_HEADER_DIVIDER,
          ),
        );
      }
    }
    return children;
  }
}

class AppTableHeaderCell extends StatelessWidget {
  final String label;
  final int flex;
  final Widget? child;
  final bool isCenter;
  final EdgeInsetsGeometry? padding;
  final double? width;

  const AppTableHeaderCell({
    super.key,
    this.label = '',
    this.flex = 1,
    this.child,
    this.isCenter = false,
    this.padding,
    this.width,
  });

  @override
  Widget build(BuildContext context) {
    final Widget content = Container(
      padding:
          padding ??
          const EdgeInsets.symmetric(
            horizontal: AppSpacing.smd,
            vertical: AppSpacing.sm,
          ),
      alignment: Alignment.center,
      child:
          child ??
          Text(
            label,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.tableHeader,
          ),
    );

    if (width != null) return SizedBox(width: width, child: content);
    if (flex > 0) return Expanded(flex: flex, child: content);
    return content;
  }
}
