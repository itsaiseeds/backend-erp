import 'package:flutter/material.dart';
import '../../theme/app_spacing.dart';

class FormFieldGrid extends StatelessWidget {
  final List<Widget> fields;

  const FormFieldGrid({super.key, required this.fields});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final int columnCount =
            constraints.maxWidth >= AppSizes.detailFieldMinWidth * 2 ? 2 : 1;

        final List<Widget> rows = [];
        for (int index = 0; index < fields.length; index += columnCount) {
          final int end = (index + columnCount) > fields.length
              ? fields.length
              : index + columnCount;
          final List<Widget> rowFields = fields.sublist(index, end);

          final List<Widget> children = [];
          for (int column = 0; column < columnCount; column++) {
            if (column > 0) children.add(const SizedBox(width: AppSpacing.lg));
            children.add(
              Expanded(
                child: column < rowFields.length
                    ? rowFields[column]
                    : const SizedBox.shrink(),
              ),
            );
          }

          if (rows.isNotEmpty) rows.add(const SizedBox(height: AppSpacing.md));
          rows.add(
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          );
        }

        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: rows,
        );
      },
    );
  }
}
