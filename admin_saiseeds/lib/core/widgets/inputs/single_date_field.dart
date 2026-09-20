import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'date_range_field.dart';

class SingleDateField extends StatefulWidget {
  final DateTime? value;
  final ValueChanged<DateTime?> onChanged;
  final bool enabled;
  final VoidCallback? onBlockedTap;

  const SingleDateField({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
    this.onBlockedTap,
  });

  @override
  State<SingleDateField> createState() => _SingleDateFieldState();
}

class _SingleDateFieldState extends State<SingleDateField> {
  static final DateFormat _display = DateFormat('d MMM yyyy');

  final LayerLink _layerLink = LayerLink();

  OverlayEntry? _overlayEntry;
  DateTime? _draft;
  late DateTime _month;

  @override
  void dispose() {
    _removeOverlay();
    super.dispose();
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  void _open() {
    if (!widget.enabled) {
      widget.onBlockedTap?.call();
      return;
    }

    final DateTime anchor = widget.value ?? DateTime.now();
    _draft = widget.value;
    _month = DateTime(anchor.year, anchor.month);

    _overlayEntry = OverlayEntry(builder: _buildOverlay);
    Overlay.of(context).insert(_overlayEntry!);
  }

  void _close() => _removeOverlay();

  void _apply() {
    final DateTime? picked = _draft;
    _removeOverlay();
    widget.onChanged(picked);
  }

  void _clear() {
    _removeOverlay();
    widget.onChanged(null);
  }

  void _select(DateTime day) {
    _draft = day;
    _overlayEntry?.markNeedsBuild();
  }

  void _shiftMonth(int delta) {
    _month = DateTime(_month.year, _month.month + delta);
    _overlayEntry?.markNeedsBuild();
  }

  Widget _buildOverlay(BuildContext overlayContext) {
    return Stack(
      children: [
        Positioned.fill(
          child: GestureDetector(
            behavior: HitTestBehavior.translucent,
            onTap: _close,
          ),
        ),
        Positioned(
          width: AppSizes.singleDatePopoverWidth,
          child: CompositedTransformFollower(
            link: _layerLink,
            showWhenUnlinked: false,
            offset: const Offset(0, AppSizes.inputHeight + AppSpacing.xs),
            child: Material(
              color: AppColors.TRANSPARENT,
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.SURFACE,
                  border: Border.all(color: AppColors.BORDER),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(AppSpacing.smd),
                      child: CalendarMonthGrid(
                        month: _month,
                        start: _draft,
                        end: _draft,
                        onPrevious: () => _shiftMonth(-1),
                        onNext: () => _shiftMonth(1),
                        onSelect: _select,
                      ),
                    ),
                    const Divider(
                      height: AppSizes.borderThin,
                      thickness: AppSizes.borderThin,
                      color: AppColors.BORDER,
                    ),
                    Padding(
                      padding: const EdgeInsets.all(AppSpacing.smd),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          _DateAction(
                            label: AppStrings.DATE_RANGE_CLEAR,
                            onTap: _clear,
                          ),
                          const SizedBox(width: AppSpacing.md),
                          _DateAction(
                            label: AppStrings.DATE_RANGE_CANCEL,
                            onTap: _close,
                          ),
                          const SizedBox(width: AppSpacing.md),
                          _DateApplyAction(
                            enabled: _draft != null,
                            onTap: _apply,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final DateTime? value = widget.value;
    final bool hasValue = value != null;

    return CompositedTransformTarget(
      link: _layerLink,
      child: MouseRegion(
        cursor: widget.enabled
            ? SystemMouseCursors.click
            : SystemMouseCursors.basic,
        child: GestureDetector(
          onTap: _open,
          child: Container(
            height: AppSizes.inputHeight,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            decoration: BoxDecoration(
              color: widget.enabled
                  ? AppColors.SURFACE
                  : AppColors.SURFACE_VARIANT,
              border: Border.all(color: AppColors.BORDER),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.event_outlined,
                  size: AppSizes.iconSm,
                  color: widget.enabled
                      ? AppColors.PRIMARY
                      : AppColors.TEXT_DISABLED,
                ),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    hasValue
                        ? _display.format(value)
                        : AppStrings.DATE_PICK_HINT,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      color: hasValue
                          ? AppColors.TEXT_PRIMARY
                          : AppColors.TEXT_DISABLED,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DateAction extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _DateAction({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: Text(
          label,
          style: AppTypography.button.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      ),
    );
  }
}

class _DateApplyAction extends StatelessWidget {
  final bool enabled;
  final VoidCallback onTap;

  const _DateApplyAction({required this.enabled, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: enabled ? onTap : null,
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          decoration: BoxDecoration(
            color: enabled ? AppColors.PRIMARY : AppColors.BORDER,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Text(
            AppStrings.DATE_RANGE_APPLY,
            style: AppTypography.button.copyWith(
              color: AppColors.TEXT_ON_PRIMARY,
            ),
          ),
        ),
      ),
    );
  }
}
