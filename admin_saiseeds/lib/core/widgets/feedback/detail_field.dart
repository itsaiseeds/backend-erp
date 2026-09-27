import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../inputs/app_text_field.dart';
import '../../theme/app_spacing.dart';

class DetailField extends StatefulWidget {
  final String label;
  final String value;

  const DetailField({super.key, required this.label, required this.value});

  @override
  State<DetailField> createState() => _DetailFieldState();
}

class _DetailFieldState extends State<DetailField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: _resolved);
  }

  @override
  void didUpdateWidget(covariant DetailField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value) _controller.text = _resolved;
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String get _resolved => widget.value.trim().isEmpty
      ? AppStrings.TABLE_VALUE_UNAVAILABLE
      : widget.value.trim();

  @override
  Widget build(BuildContext context) {
    return AppTextField(
      label: widget.label,
      controller: _controller,
      enabled: false,
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
