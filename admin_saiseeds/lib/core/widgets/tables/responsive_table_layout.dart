import 'package:flutter/material.dart';
import '../../theme/app_spacing.dart';

typedef ResponsiveTableBuilder =
    Widget Function(BuildContext context, int itemsPerPage);

class ResponsiveTableLayout extends StatelessWidget {
  final ResponsiveTableBuilder builder;
  final double rowHeight;
  final double overheadHeight;

  const ResponsiveTableLayout({
    super.key,
    required this.builder,
    this.rowHeight = AppSizes.tableRowHeight,
    this.overheadHeight = AppSizes.tableOverheadHeight,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final double availableHeight = constraints.maxHeight.isFinite
            ? constraints.maxHeight - overheadHeight
            : rowHeight;
        int itemsPerPage = (availableHeight / rowHeight).floor();
        if (itemsPerPage < 1) itemsPerPage = 1;
        return builder(context, itemsPerPage);
      },
    );
  }
}
