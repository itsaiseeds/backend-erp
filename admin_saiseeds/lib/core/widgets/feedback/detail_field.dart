import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class DetailField extends StatelessWidget {
  final String label;
  final String value;

  const DetailField({super.key, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final String resolved = value.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : value.trim();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: AppTypography.labelSmall.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
        ),
        const SizedBox(height: AppSpacing.xxs),
        Text(resolved, style: AppTypography.bodyMedium),
      ],
    );
  }
}

class DetailFieldGrid extends StatelessWidget {
  final List<DetailField> fields;

  const DetailFieldGrid({super.key, required this.fields});

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
          final List<DetailField> rowFields = fields.sublist(index, end);

          final List<Widget> children = [];
          for (int column = 0; column < columnCount; column++) {
            if (column > 0) {
              children.add(const SizedBox(width: AppSpacing.lg));
            }
            children.add(
              Expanded(
                child: column < rowFields.length
                    ? rowFields[column]
                    : const SizedBox.shrink(),
              ),
            );
          }

          if (rows.isNotEmpty) {
            rows.add(const SizedBox(height: AppSpacing.md));
          }
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
