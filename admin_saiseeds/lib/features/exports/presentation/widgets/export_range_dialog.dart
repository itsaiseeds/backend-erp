import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../data/models/export_kind.dart';
import '../bloc/exports_cubit.dart';

/// Asks for the date window, then builds and downloads the report.
class ExportRangeDialog extends StatefulWidget {
  final ExportKind kind;

  const ExportRangeDialog({super.key, required this.kind});

  static final DateFormat isoDate = DateFormat('yyyy-MM-dd');

  /// The API caps a window at 31 days including both ends.
  static const int maxWindowDays = 31;

  static Future<void> show(
    BuildContext context, {
    required ExportsCubit cubit,
    required ExportKind kind,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<ExportsCubit>.value(
        value: cubit,
        child: ExportRangeDialog(kind: kind),
      ),
    );
  }

  @override
  State<ExportRangeDialog> createState() => _ExportRangeDialogState();
}

class _ExportRangeDialogState extends State<ExportRangeDialog> {
  /// Only the windows the API will actually accept: it caps an export at
  /// 31 days, so a "Last 90 days" shortcut could only ever fail.
  static const List<DateRangePreset> _presets = [
    DateRangePreset(AppStrings.DATE_RANGE_TODAY, 0),
    DateRangePreset(AppStrings.DATE_RANGE_LAST_7, 7),
    DateRangePreset(AppStrings.DATE_RANGE_LAST_30, 30),
  ];

  DateTime? _start;
  DateTime? _end;
  ExportFormat _format = ExportFormat.spreadsheet;
  bool _isSubmitting = false;
  String? _error;

  String get _rangeValue =>
      DateRangeValue(start: _start, end: _end).wireValue;

  void _onRangeChanged(String raw) {
    final DateRangeValue parsed = DateRangeValue.parse(raw);
    setState(() {
      _start = parsed.start;
      _end = parsed.end;
      _error = null;
    });
  }

  /// Inventory snapshots may be run for all history, so its window is not
  /// required; every other report needs one.
  bool get _isWindowOptional => widget.kind.isPaginated;

  @override
  void initState() {
    super.initState();
    if (!_isWindowOptional) {
      final DateTime today = DateTime.now();
      _start = DateTime(today.year, today.month, today.day);
      _end = _start;
    }
  }

  String? _validate() {
    final bool hasStart = _start != null;
    final bool hasEnd = _end != null;

    if (_isWindowOptional && !hasStart && !hasEnd) return null;
    if (!hasStart || !hasEnd) return AppStrings.EXPORT_RANGE_REQUIRED;
    if (_end!.isBefore(_start!)) return AppStrings.EXPORT_RANGE_BACKWARDS;

    final int span = _end!.difference(_start!).inDays + 1;
    if (span > ExportRangeDialog.maxWindowDays) {
      return AppStrings.EXPORT_RANGE_TOO_LONG;
    }
    return null;
  }

  Future<void> _submit() async {
    final String? problem = _validate();
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }

    setState(() {
      _error = null;
      _isSubmitting = true;
    });

    final ExportsCubit cubit = context.read<ExportsCubit>();
    final ExportResult result = await cubit.export(
      kind: widget.kind,
      format: _format,
      startDate: _start == null
          ? null
          : ExportRangeDialog.isoDate.format(_start!),
      endDate: _end == null ? null : ExportRangeDialog.isoDate.format(_end!),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    switch (result.outcome) {
      case ExportOutcome.success:
        Navigator.of(context).pop();
        ToastUtils.showSuccess(
          context,
          _format == ExportFormat.receipts
              ? AppStrings.EXPORT_RECEIPTS_DONE
              : AppStrings.EXPORT_DONE,
          description:
              '${result.rowCount} '
              '${result.rowCount == 1 ? AppStrings.EXPORT_ROWS_ONE : AppStrings.EXPORT_ROWS_MANY}'
              ' · ${widget.kind.label}',
        );
      case ExportOutcome.empty:
        setState(() => _error = AppStrings.EXPORT_EMPTY);
      case ExportOutcome.failure:
        setState(
          () => _error = result.errorMessage ?? AppStrings.EXPORT_FAILED,
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: widget.kind.icon,
      title: widget.kind.label,
      subtitle: AppStrings.EXPORT_DIALOG_SUBTITLE,
      // A date picker needs nowhere near the default 900px.
      width: AppSizes.formDialogCompactWidth,
      submitLabel: AppStrings.EXPORT,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.smd),
            decoration: BoxDecoration(
              color: AppColors.SURFACE_VARIANT,
              borderRadius: BorderRadius.circular(AppRadius.sm),
              border: Border.all(color: AppColors.BORDER),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  widget.kind.icon,
                  size: AppSizes.iconSm,
                  color: AppColors.TEXT_SECONDARY,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    widget.kind.description,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (widget.kind.supportsReceipts) ...[
            const SizedBox(height: AppSpacing.md),
            Text(AppStrings.EXPORT_FORMAT_LABEL, style: AppTypography.label),
            const SizedBox(height: AppSpacing.xs),
            _FormatChoice(
              value: _format,
              enabled: !_isSubmitting,
              onChanged: (next) => setState(() {
                _format = next;
                _error = null;
              }),
            ),
          ],
          const SizedBox(height: AppSpacing.md),
          Text(AppStrings.EXPORT_RANGE_LABEL, style: AppTypography.label),
          const SizedBox(height: AppSpacing.xs),
          DateRangeField(
            value: _rangeValue,
            enabled: !_isSubmitting,
            presets: _presets,
            onChanged: _onRangeChanged,
          ),
          if (_isWindowOptional) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              AppStrings.EXPORT_WINDOW_OPTIONAL,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
            ),
          ],
        ],
      ),
    );
  }
}


/// Spreadsheet or a zip of challans. Two options, so both stay visible
/// rather than hiding behind a dropdown.
class _FormatChoice extends StatelessWidget {
  final ExportFormat value;
  final bool enabled;
  final ValueChanged<ExportFormat> onChanged;

  const _FormatChoice({
    required this.value,
    required this.enabled,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _FormatTile(
            icon: Icons.table_chart_outlined,
            label: AppStrings.EXPORT_FORMAT_SHEET,
            caption: AppStrings.EXPORT_FORMAT_SHEET_BODY,
            isSelected: value == ExportFormat.spreadsheet,
            enabled: enabled,
            onTap: () => onChanged(ExportFormat.spreadsheet),
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          child: _FormatTile(
            icon: Icons.picture_as_pdf_outlined,
            label: AppStrings.EXPORT_FORMAT_RECEIPTS,
            caption: AppStrings.EXPORT_FORMAT_RECEIPTS_BODY,
            isSelected: value == ExportFormat.receipts,
            enabled: enabled,
            onTap: () => onChanged(ExportFormat.receipts),
          ),
        ),
      ],
    );
  }
}

class _FormatTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String caption;
  final bool isSelected;
  final bool enabled;
  final VoidCallback onTap;

  const _FormatTile({
    required this.icon,
    required this.label,
    required this.caption,
    required this.isSelected,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color tone = isSelected
        ? AppColors.PRIMARY
        : AppColors.TEXT_SECONDARY;

    return MouseRegion(
      cursor: enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: enabled ? onTap : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.all(AppSpacing.smd),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.PRIMARY_SURFACE : AppColors.SURFACE,
            border: Border.all(
              color: isSelected ? AppColors.PRIMARY : AppColors.BORDER,
              width: isSelected
                  ? AppSizes.borderMedium
                  : AppSizes.borderThin,
            ),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  Icon(icon, size: AppSizes.iconSm, color: tone),
                  const SizedBox(width: AppSpacing.sm),
                  Expanded(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.bodySmall.copyWith(
                        fontWeight: FontWeight.w600,
                        color: isSelected
                            ? AppColors.PRIMARY_DARK
                            : AppColors.TEXT_PRIMARY,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                caption,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
