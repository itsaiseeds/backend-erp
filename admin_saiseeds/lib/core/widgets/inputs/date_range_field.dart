import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class DateRangeValue {
  static const String SEPARATOR = '|';

  final DateTime? start;
  final DateTime? end;

  const DateRangeValue({this.start, this.end});

  static final DateFormat _wire = DateFormat('yyyy-MM-dd');
  static final DateFormat _display = DateFormat('d MMM yyyy');

  factory DateRangeValue.parse(String raw) {
    final List<String> parts = raw.split(SEPARATOR);
    return DateRangeValue(
      start: _tryParse(parts.isNotEmpty ? parts.first : ''),
      end: _tryParse(parts.length > 1 ? parts[1] : ''),
    );
  }

  static DateTime? _tryParse(String value) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty) return null;
    return DateTime.tryParse(trimmed);
  }

  bool get isEmpty => start == null && end == null;

  String get wireValue {
    final String from = start == null ? '' : _wire.format(start!);
    final String to = end == null ? '' : _wire.format(end!);
    return '$from$SEPARATOR$to';
  }

  String get displayValue {
    if (isEmpty) return '';
    final String from = start == null ? '' : _display.format(start!);
    final String to = end == null ? '' : _display.format(end!);
    if (from.isEmpty) return '${AppStrings.DATE_RANGE_UNTIL} $to';
    if (to.isEmpty) return '${AppStrings.DATE_RANGE_FROM} $from';
    return '$from ${AppStrings.DATE_RANGE_ARROW} $to';
  }
}

class _Preset {
  final String label;
  final int days;

  const _Preset(this.label, this.days);
}

class DateRangeField extends StatefulWidget {
  final String value;
  final ValueChanged<String> onChanged;
  final bool enabled;

  const DateRangeField({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  State<DateRangeField> createState() => _DateRangeFieldState();
}

class _DateRangeFieldState extends State<DateRangeField> {
  static const List<_Preset> _presets = [
    _Preset(AppStrings.DATE_RANGE_TODAY, 0),
    _Preset(AppStrings.DATE_RANGE_LAST_7, 7),
    _Preset(AppStrings.DATE_RANGE_LAST_30, 30),
    _Preset(AppStrings.DATE_RANGE_LAST_90, 90),
    _Preset(AppStrings.DATE_RANGE_LAST_6M, 182),
    _Preset(AppStrings.DATE_RANGE_LAST_YEAR, 365),
  ];

  final LayerLink _layerLink = LayerLink();

  OverlayEntry? _overlayEntry;
  DateTime? _draftStart;
  DateTime? _draftEnd;
  DateTime _leftMonth = DateTime.now();

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
    final DateRangeValue current = DateRangeValue.parse(widget.value);
    final DateTime now = DateTime.now();
    final DateTime anchor = current.start ?? now;

    _draftStart = current.start;
    _draftEnd = current.end;
    _leftMonth = DateTime(anchor.year, anchor.month);

    _overlayEntry = OverlayEntry(builder: _buildOverlay);
    Overlay.of(context).insert(_overlayEntry!);
  }

  void _close() => _removeOverlay();

  void _rebuildOverlay() => _overlayEntry?.markNeedsBuild();

  void _applyPreset(_Preset preset) {
    final DateTime now = DateTime.now();
    final DateTime end = DateTime(now.year, now.month, now.day);

    _draftEnd = end;
    _draftStart = preset.days == 0
        ? end
        : end.subtract(Duration(days: preset.days));
    _leftMonth = DateTime(_draftStart!.year, _draftStart!.month);
    _rebuildOverlay();
  }

  void _selectDay(DateTime day) {
    if (_draftStart == null || _draftEnd != null) {
      _draftStart = day;
      _draftEnd = null;
      _rebuildOverlay();
      return;
    }

    if (day.isBefore(_draftStart!)) {
      _draftEnd = _draftStart;
      _draftStart = day;
    } else {
      _draftEnd = day;
    }
    _rebuildOverlay();
  }

  void _apply() {
    final DateRangeValue next = DateRangeValue(
      start: _draftStart,
      end: _draftEnd ?? _draftStart,
    );
    _removeOverlay();
    widget.onChanged(next.isEmpty ? '' : next.wireValue);
  }

  void _clear() {
    _removeOverlay();
    widget.onChanged('');
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
          width: AppSizes.dateRangePopoverWidth,
          child: CompositedTransformFollower(
            link: _layerLink,
            showWhenUnlinked: false,
            offset: const Offset(0, AppSizes.tableControlHeight),
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
                    IntrinsicHeight(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _buildPresets(),
                          const VerticalDivider(
                            width: AppSizes.borderThin,
                            thickness: AppSizes.borderThin,
                            color: AppColors.BORDER,
                          ),
                          Expanded(child: _buildCalendars()),
                        ],
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
                          _TextAction(
                            label: AppStrings.DATE_RANGE_CLEAR,
                            onTap: _clear,
                          ),
                          const SizedBox(width: AppSpacing.md),
                          _TextAction(
                            label: AppStrings.DATE_RANGE_CANCEL,
                            onTap: _close,
                          ),
                          const SizedBox(width: AppSpacing.md),
                          _ApplyAction(
                            enabled: _draftStart != null,
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

  Widget _buildCalendars() {
    final DateTime rightMonth = DateTime(_leftMonth.year, _leftMonth.month + 1);

    return Padding(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _MonthGrid(
              month: _leftMonth,
              start: _draftStart,
              end: _draftEnd,
              onPrevious: () {
                _leftMonth = DateTime(_leftMonth.year, _leftMonth.month - 1);
                _rebuildOverlay();
              },
              onSelect: _selectDay,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: _MonthGrid(
              month: rightMonth,
              start: _draftStart,
              end: _draftEnd,
              onNext: () {
                _leftMonth = DateTime(_leftMonth.year, _leftMonth.month + 1);
                _rebuildOverlay();
              },
              onSelect: _selectDay,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPresets() {
    return SizedBox(
      width: AppSizes.dateRangePresetsWidth,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final preset in _presets)
            InkWell(
              onTap: () => _applyPreset(preset),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSpacing.smd,
                ),
                child: Text(preset.label, style: AppTypography.bodySmall),
              ),
            ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final DateRangeValue parsed = DateRangeValue.parse(widget.value);
    final String label = parsed.isEmpty
        ? AppStrings.DATE_RANGE_HINT
        : parsed.displayValue;

    return CompositedTransformTarget(
      link: _layerLink,
      child: GestureDetector(
        onTap: widget.enabled ? _open : null,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Flexible(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelMedium.copyWith(
                  color: parsed.isEmpty
                      ? AppColors.TEXT_DISABLED
                      : AppColors.TEXT_PRIMARY,
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            const Icon(
              Icons.calendar_today_rounded,
              size: AppSizes.iconSm,
              color: AppColors.TEXT_SECONDARY,
            ),
          ],
        ),
      ),
    );
  }
}

class _MonthGrid extends StatelessWidget {
  final DateTime month;
  final DateTime? start;
  final DateTime? end;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final ValueChanged<DateTime> onSelect;

  const _MonthGrid({
    required this.month,
    required this.start,
    required this.end,
    required this.onSelect,
    this.onPrevious,
    this.onNext,
  });

  static final DateFormat _title = DateFormat('MMMM yyyy');
  static const List<String> _weekdays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

  static DateTime _dayOnly(DateTime value) =>
      DateTime(value.year, value.month, value.day);

  bool _isInRange(DateTime day) {
    if (start == null || end == null) return false;
    final DateTime d = _dayOnly(day);
    return !d.isBefore(_dayOnly(start!)) && !d.isAfter(_dayOnly(end!));
  }

  bool _isEndpoint(DateTime day) {
    final DateTime d = _dayOnly(day);
    if (start != null && d == _dayOnly(start!)) return true;
    if (end != null && d == _dayOnly(end!)) return true;
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final int daysInMonth = DateTime(month.year, month.month + 1, 0).day;
    final int leadingBlanks = DateTime(month.year, month.month).weekday % 7;

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            SizedBox(
              width: AppSizes.dateRangeCellSize,
              child: onPrevious == null
                  ? null
                  : _NavIcon(
                      icon: Icons.chevron_left_rounded,
                      onTap: onPrevious!,
                    ),
            ),
            Expanded(
              child: Text(
                _title.format(month),
                textAlign: TextAlign.center,
                style: AppTypography.labelStrong,
              ),
            ),
            SizedBox(
              width: AppSizes.dateRangeCellSize,
              child: onNext == null
                  ? null
                  : _NavIcon(icon: Icons.chevron_right_rounded, onTap: onNext!),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            for (final day in _weekdays)
              Expanded(
                child: Text(
                  day,
                  textAlign: TextAlign.center,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: AppSpacing.xs),
        for (int week = 0; week < 6; week++)
          if (week * 7 < leadingBlanks + daysInMonth)
            Row(
              children: [
                for (int slot = 0; slot < 7; slot++)
                  Expanded(
                    child: _buildCell(week * 7 + slot, leadingBlanks, daysInMonth),
                  ),
              ],
            ),
      ],
    );
  }

  Widget _buildCell(int index, int leadingBlanks, int daysInMonth) {
    final int dayNumber = index - leadingBlanks + 1;
    if (dayNumber < 1 || dayNumber > daysInMonth) {
      return const SizedBox(height: AppSizes.dateRangeCellSize);
    }

    final DateTime day = DateTime(month.year, month.month, dayNumber);
    final bool isEndpoint = _isEndpoint(day);
    final bool inRange = _isInRange(day);

    return InkWell(
      onTap: () => onSelect(day),
      child: Container(
        height: AppSizes.dateRangeCellSize,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: isEndpoint
              ? AppColors.PRIMARY
              : (inRange ? AppColors.PRIMARY_SURFACE : AppColors.TRANSPARENT),
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Text(
          '$dayNumber',
          style: AppTypography.bodySmall.copyWith(
            color: isEndpoint
                ? AppColors.TEXT_ON_PRIMARY
                : AppColors.TEXT_PRIMARY,
          ),
        ),
      ),
    );
  }
}

class _NavIcon extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _NavIcon({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Icon(
        icon,
        size: AppSizes.iconMd,
        color: AppColors.TEXT_SECONDARY,
      ),
    );
  }
}

class _TextAction extends StatelessWidget {
  final String label;
  final VoidCallback onTap;

  const _TextAction({required this.label, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.sm,
          vertical: AppSpacing.xs,
        ),
        child: Text(
          label,
          style: AppTypography.labelMedium.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      ),
    );
  }
}

class _ApplyAction extends StatelessWidget {
  final bool enabled;
  final VoidCallback onTap;

  const _ApplyAction({required this.enabled, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: enabled ? onTap : null,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          color: enabled ? AppColors.PRIMARY : AppColors.SURFACE_VARIANT,
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
        child: Text(
          AppStrings.DATE_RANGE_APPLY,
          style: AppTypography.labelMedium.copyWith(
            color: enabled
                ? AppColors.TEXT_ON_PRIMARY
                : AppColors.TEXT_DISABLED,
          ),
        ),
      ),
    );
  }
}
