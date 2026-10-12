import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../data/models/export_kind.dart';
import '../bloc/exports_cubit.dart';

/// Asks which output a kind with more than one format should download as --
/// a spreadsheet plus challans for dispatch receipts, or a spreadsheet plus
/// the lab tester's own PDF for lab testings. Only shown for a kind whose
/// [ExportKindX.hasFormatChoice] is true; everything else downloads the
/// spreadsheet straight away with no prompt.
class ExportFormatDialog extends StatefulWidget {
  final ExportKind kind;

  const ExportFormatDialog({super.key, required this.kind});

  /// Answers the chosen format, or null if the popup was dismissed without
  /// one -- the caller should treat null as "cancelled", not "spreadsheet".
  static Future<ExportFormat?> show(
    BuildContext context, {
    required ExportKind kind,
  }) {
    return showDialog<ExportFormat>(
      context: context,
      builder: (_) => ExportFormatDialog(kind: kind),
    );
  }

  @override
  State<ExportFormatDialog> createState() => _ExportFormatDialogState();
}

class _ExportFormatDialogState extends State<ExportFormatDialog> {
  ExportFormat _format = ExportFormat.spreadsheet;

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: widget.kind.icon,
      title: widget.kind.label,
      subtitle: AppStrings.EXPORT_FORMAT_LABEL,
      width: AppSizes.formDialogCompactWidth,
      submitLabel: AppStrings.EXPORT,
      onSubmit: () => Navigator.of(context).pop(_format),
      content: _FormatChoice(
        value: _format,
        secondFormat: widget.kind.supportsReceipts
            ? ExportFormat.receipts
            : ExportFormat.pdfReport,
        secondIcon: widget.kind.supportsReceipts
            ? Icons.picture_as_pdf_outlined
            : Icons.description_outlined,
        secondLabel: widget.kind.supportsReceipts
            ? AppStrings.EXPORT_FORMAT_RECEIPTS
            : AppStrings.EXPORT_FORMAT_PDF_REPORT,
        secondCaption: widget.kind.supportsReceipts
            ? AppStrings.EXPORT_FORMAT_RECEIPTS_BODY
            : AppStrings.EXPORT_FORMAT_PDF_REPORT_BODY,
        enabled: true,
        onChanged: (next) => setState(() => _format = next),
      ),
    );
  }
}

/// Spreadsheet plus one other format. Two options, so both stay visible
/// rather than hiding behind a dropdown.
class _FormatChoice extends StatelessWidget {
  final ExportFormat value;
  final ExportFormat secondFormat;
  final IconData secondIcon;
  final String secondLabel;
  final String secondCaption;
  final bool enabled;
  final ValueChanged<ExportFormat> onChanged;

  const _FormatChoice({
    required this.value,
    required this.secondFormat,
    required this.secondIcon,
    required this.secondLabel,
    required this.secondCaption,
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
            icon: secondIcon,
            label: secondLabel,
            caption: secondCaption,
            isSelected: value == secondFormat,
            enabled: enabled,
            onTap: () => onChanged(secondFormat),
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
              width: isSelected ? AppSizes.borderMedium : AppSizes.borderThin,
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
                      style: AppTypography.labelStrong.copyWith(color: tone),
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
