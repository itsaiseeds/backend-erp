import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';

class ColumnResizeHandle extends StatelessWidget {
  final ValueChanged<double> onDrag;
  final double height;

  const ColumnResizeHandle({
    super.key,
    required this.onDrag,
    this.height = AppSizes.tableHeaderHeight,
  });

  static double minWidthFor(String columnId) {
    if (columnId == AppStrings.TABLE_SELECT_COLUMN_LABEL) {
      return AppSizes.tableMinSelectColumnWidth;
    }
    if (columnId == AppStrings.TABLE_ACTIONS_COLUMN_LABEL) {
      return AppSizes.tableMinActionColumnWidth;
    }
    return AppSizes.tableMinColumnWidth;
  }

  static double clampWidth(
    double current,
    double delta, {
    double minWidth = AppSizes.tableMinColumnWidth,
  }) {
    return (current + delta).clamp(minWidth, AppSizes.tableMaxColumnWidth);
  }

  @override
  Widget build(BuildContext context) {
    return SelectionContainer.disabled(
      child: MouseRegion(
        cursor: SystemMouseCursors.resizeColumn,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onHorizontalDragStart: (_) {},
          onHorizontalDragUpdate: (details) => onDrag(details.delta.dx),
          child: Tooltip(
            message: AppStrings.TABLE_RESIZE_COLUMN,
            child: SizedBox(
              width: AppSizes.tableResizeHandleWidth,
              height: height,
              child: const Center(
                child: SizedBox(
                  width: AppSizes.borderThin,
                  height: AppSizes.tableResizeGripHeight,
                  child: ColoredBox(color: AppColors.TABLE_HEADER_DIVIDER),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class ColumnBodyDivider extends StatelessWidget {
  const ColumnBodyDivider({super.key});

  @override
  Widget build(BuildContext context) {
    return const SizedBox(
      width: AppSizes.tableResizeHandleWidth,
      child: Center(
        child: VerticalDivider(
          width: AppSizes.borderThin,
          thickness: AppSizes.borderThin,
          color: AppColors.TABLE_ROW_DIVIDER,
        ),
      ),
    );
  }
}

class TableHeaderScrollLayer extends StatelessWidget {
  final double offset;
  final double width;
  final Widget child;

  const TableHeaderScrollLayer({
    super.key,
    required this.offset,
    required this.width,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.hardEdge,
      children: [
        Positioned(
          left: -offset,
          top: 0,
          bottom: 0,
          width: width,
          child: child,
        ),
      ],
    );
  }
}
