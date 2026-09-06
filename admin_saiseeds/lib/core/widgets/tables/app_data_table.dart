import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppDataTable extends StatelessWidget {
  final List<String> columns;
  final List<List<Widget>> rows;
  final List<int>? columnFlex;
  final bool alternateRowColor;

  const AppDataTable({
    super.key,
    required this.columns,
    required this.rows,
    this.columnFlex,
    this.alternateRowColor = false,
  });

  List<int> get _flex => columnFlex ?? List.filled(columns.length, 1);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _AppDataTableHeaderRow(columns: columns, flex: _flex),
          for (int i = 0; i < rows.length; i++)
            _AppDataTableRow(
              cells: rows[i],
              flex: _flex,
              isLast: i == rows.length - 1,
              background: alternateRowColor && i.isOdd
                  ? AppColors.SURFACE_VARIANT
                  : AppColors.SURFACE,
            ),
        ],
      ),
    );
  }
}

class _AppDataTableHeaderRow extends StatelessWidget {
  final List<String> columns;
  final List<int> flex;

  const _AppDataTableHeaderRow({required this.columns, required this.flex});

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppColors.SURFACE_VARIANT,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.md,
        vertical: AppSpacing.sm,
      ),
      child: Row(
        children: [
          for (int i = 0; i < columns.length; i++)
            Expanded(
              flex: flex[i],
              child: Text(
                columns[i],
                style: AppTypography.label,
                overflow: TextOverflow.ellipsis,
              ),
            ),
        ],
      ),
    );
  }
}

class _AppDataTableRow extends StatefulWidget {
  final List<Widget> cells;
  final List<int> flex;
  final bool isLast;
  final Color background;

  const _AppDataTableRow({
    required this.cells,
    required this.flex,
    required this.isLast,
    required this.background,
  });

  @override
  State<_AppDataTableRow> createState() => _AppDataTableRowState();
}

class _AppDataTableRowState extends State<_AppDataTableRow> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: _isHovered ? AppColors.PRIMARY_SURFACE : widget.background,
          border: widget.isLast
              ? null
              : const Border(bottom: BorderSide(color: AppColors.DIVIDER)),
        ),
        child: Row(
          children: [
            for (int i = 0; i < widget.cells.length; i++)
              Expanded(flex: widget.flex[i], child: widget.cells[i]),
          ],
        ),
      ),
    );
  }
}
