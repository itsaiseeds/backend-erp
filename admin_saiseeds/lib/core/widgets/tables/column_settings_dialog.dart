import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../buttons/primary_button.dart';
import '../dialogs/app_dialog_shell.dart';
import 'app_data_column.dart';

class ColumnSettingsDialog extends StatefulWidget {
  final String title;
  final String subtitle;
  final List<AppDataColumn> columns;
  final List<String> hiddenColumns;
  final List<String> excludedColumnIds;
  final ValueChanged<String> onToggle;

  const ColumnSettingsDialog({
    super.key,
    this.title = AppStrings.TABLE_COLUMN_SETTINGS_TITLE,
    this.subtitle = AppStrings.TABLE_COLUMN_SETTINGS_SUBTITLE,
    required this.columns,
    required this.hiddenColumns,
    this.excludedColumnIds = const [],
    required this.onToggle,
  });

  @override
  State<ColumnSettingsDialog> createState() => _ColumnSettingsDialogState();
}

class _ColumnSettingsDialogState extends State<ColumnSettingsDialog> {
  late List<String> _hidden;

  @override
  void initState() {
    super.initState();
    _hidden = List<String>.from(widget.hiddenColumns);
  }

  void _toggle(String columnId) {
    widget.onToggle(columnId);
    setState(() {
      if (_hidden.contains(columnId)) {
        _hidden.remove(columnId);
      } else {
        _hidden.add(columnId);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final List<AppDataColumn> selectable = widget.columns
        .where((column) => !widget.excludedColumnIds.contains(column.id))
        .toList();

    return AppDialogShell(
      title: widget.title,
      width: AppSizes.tableSettingsDialogWidth,
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.subtitle,
            style: AppTypography.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          Flexible(
            child: SingleChildScrollView(
              child: Wrap(
                spacing: AppSpacing.smd,
                runSpacing: AppSpacing.smd,
                children: selectable
                    .map(
                      (column) => _ColumnToggleTile(
                        label: column.label,
                        isHidden: _hidden.contains(column.id),
                        onToggle: () => _toggle(column.id),
                      ),
                    )
                    .toList(),
              ),
            ),
          ),
        ],
      ),
      actions: [
        PrimaryButton(
          label: AppStrings.TABLE_COLUMN_SETTINGS_DONE,
          onPressed: () => Navigator.of(context).pop(),
        ),
      ],
    );
  }
}

class _ColumnToggleTile extends StatelessWidget {
  final String label;
  final bool isHidden;
  final VoidCallback onToggle;

  const _ColumnToggleTile({
    required this.label,
    required this.isHidden,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: AppSizes.tableSettingsTileWidth,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.smd,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: isHidden ? AppColors.SURFACE_VARIANT : AppColors.PRIMARY_SURFACE,
          borderRadius: BorderRadius.circular(AppRadius.md),
          border: Border.all(
            color: isHidden ? AppColors.BORDER : AppColors.PRIMARY_LIGHT,
          ),
        ),
        child: Row(
          children: [
            Icon(
              isHidden
                  ? Icons.visibility_off_outlined
                  : Icons.visibility_outlined,
              size: AppSizes.iconMd,
              color: isHidden ? AppColors.TEXT_SECONDARY : AppColors.PRIMARY,
            ),
            const SizedBox(width: AppSpacing.smd),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelMedium.copyWith(
                  color: isHidden
                      ? AppColors.TEXT_SECONDARY
                      : AppColors.TEXT_PRIMARY,
                ),
              ),
            ),
            Switch(
              value: !isHidden,
              activeThumbColor: AppColors.WHITE,
              activeTrackColor: AppColors.PRIMARY,
              inactiveThumbColor: AppColors.WHITE,
              inactiveTrackColor: AppColors.BORDER_STRONG,
              onChanged: (_) => onToggle(),
            ),
          ],
        ),
      ),
    );
  }
}
