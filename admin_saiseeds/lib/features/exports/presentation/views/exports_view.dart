import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/inputs/date_range_field.dart';
import '../../data/exports_repository.dart';
import '../../data/models/export_kind.dart';
import '../bloc/exports_cubit.dart';
import '../widgets/export_format_dialog.dart';

class ExportsView extends StatelessWidget {
  const ExportsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<ExportsCubit>(
      create: (context) =>
          ExportsCubit(repository: ExportsRepository(apiClient: apiClient)),
      child: const _ExportsContent(),
    );
  }
}

class _ExportsContent extends StatelessWidget {
  const _ExportsContent();

  static const double _maxContentWidth = 1180;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ExportsCubit, ExportsState>(
      builder: (context, state) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: _maxContentWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const _Header(),
                  const SizedBox(height: AppSpacing.lg),
                  _ExportTable(state: state),
                  const SizedBox(height: AppSpacing.lg),
                  const _Hints(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Every export in one table: a green header matching every other list in
/// the app (`AppDataTable`'s own header styling), then one divider-separated,
/// zebra-striped row per report -- report on the left, its date range in the
/// middle, the download action on the right.
class _ExportTable extends StatelessWidget {
  final ExportsState state;

  const _ExportTable({required this.state});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.BORDER),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const _TableHeaderRow(),
          for (int i = 0; i < ExportKind.values.length; i++)
            _ExportRow(
              kind: ExportKind.values[i],
              state: state,
              isOdd: i.isOdd,
            ),
        ],
      ),
    );
  }
}

class _TableHeaderRow extends StatelessWidget {
  const _TableHeaderRow();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: AppSizes.tableHeaderHeight,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: const BoxDecoration(
        color: AppColors.TABLE_HEADER_BG,
        border: Border(bottom: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 5,
            child: Text(
              AppStrings.EXPORT_COLUMN_REPORT,
              style: AppTypography.tableHeader,
            ),
          ),
          SizedBox(
            width: 340,
            child: Text(
              AppStrings.EXPORT_COLUMN_DATE_RANGE,
              style: AppTypography.tableHeader,
            ),
          ),
          SizedBox(
            width: 140,
            child: Text(
              AppStrings.EXPORT_COLUMN_ACTION,
              textAlign: TextAlign.right,
              style: AppTypography.tableHeader,
            ),
          ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: AppSizes.exportHeaderTile,
          height: AppSizes.exportHeaderTile,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.PRIMARY_SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: const Icon(
            Icons.download_outlined,
            size: AppSizes.iconXl,
            color: AppColors.PRIMARY,
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(AppStrings.EXPORTS, style: AppTypography.headingSmall),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                AppStrings.EXPORT_SUBTITLE,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Hints extends StatelessWidget {
  const _Hints();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(
                Icons.lightbulb_outline_rounded,
                size: AppSizes.iconSm,
                color: AppColors.TEXT_SECONDARY,
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                AppStrings.EXPORT_HINT_TITLE,
                style: AppTypography.labelStrong.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          for (final String hint in const [
            AppStrings.EXPORT_HINT_WINDOW,
            AppStrings.EXPORT_HINT_ROWS,
            AppStrings.EXPORT_HINT_HISTORY,
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
              child: Text(
                '·  $hint',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// One export, one table row: the report on the left, its date range inline
/// in the middle (skipped entirely for a kind with no date window), and a
/// download action on the right. A kind that offers more than one output
/// format (a spreadsheet plus challans or a PDF report) asks which one via a
/// small popup before building; everything else downloads the spreadsheet
/// straight away.
class _ExportRow extends StatefulWidget {
  final ExportKind kind;
  final ExportsState state;
  final bool isOdd;

  const _ExportRow({
    required this.kind,
    required this.state,
    required this.isOdd,
  });

  @override
  State<_ExportRow> createState() => _ExportRowState();
}

class _ExportRowState extends State<_ExportRow> {
  static final DateFormat _isoDate = DateFormat('yyyy-MM-dd');

  /// Only the windows the API will actually accept: it caps an export at
  /// 31 days, so a "Last 90 days" shortcut could only ever fail.
  static const List<DateRangePreset> _presets = [
    DateRangePreset(AppStrings.DATE_RANGE_TODAY, 0),
    DateRangePreset(AppStrings.DATE_RANGE_LAST_7, 7),
    DateRangePreset(AppStrings.DATE_RANGE_LAST_30, 30),
    DateRangePreset(AppStrings.DATE_RANGE_LAST_60, 60),
  ];

  DateTime? _start;
  DateTime? _end;
  bool _isHovered = false;
  String? _error;

  bool get _isWindowOptional => widget.kind.isPaginated;

  @override
  void initState() {
    super.initState();
    if (!_isWindowOptional && !widget.kind.hasNoDateWindow) {
      final DateTime today = DateTime.now();
      _start = DateTime(today.year, today.month, today.day);
      _end = _start;
    }
  }

  String get _rangeValue => DateRangeValue(start: _start, end: _end).wireValue;

  void _onRangeChanged(String raw) {
    final DateRangeValue parsed = DateRangeValue.parse(raw);
    setState(() {
      _start = parsed.start;
      _end = parsed.end;
      _error = null;
    });
  }

  String? _validate() {
    if (widget.kind.hasNoDateWindow) return null;

    final bool hasStart = _start != null;
    final bool hasEnd = _end != null;

    if (_isWindowOptional && !hasStart && !hasEnd) return null;
    if (!hasStart || !hasEnd) return AppStrings.EXPORT_RANGE_REQUIRED;
    if (_end!.isBefore(_start!)) return AppStrings.EXPORT_RANGE_BACKWARDS;

    final int span = _end!.difference(_start!).inDays + 1;
    if (span > 62) return AppStrings.EXPORT_RANGE_TOO_LONG;
    return null;
  }

  Future<void> _onDownload() async {
    final String? problem = _validate();
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }
    setState(() => _error = null);

    if (!widget.kind.hasFormatChoice) {
      await _submit(ExportFormat.spreadsheet);
      return;
    }

    // Popup cancelled (barrier tap or close) answers null -- stop rather
    // than silently defaulting to a spreadsheet the user did not ask for.
    final ExportFormat? format = await ExportFormatDialog.show(
      context,
      kind: widget.kind,
    );
    if (format == null || !mounted) return;

    await _submit(format);
  }

  Future<void> _submit(ExportFormat format) async {
    final ExportsCubit cubit = context.read<ExportsCubit>();
    final ExportResult result = await cubit.export(
      kind: widget.kind,
      format: format,
      startDate: _start == null ? null : _isoDate.format(_start!),
      endDate: _end == null ? null : _isoDate.format(_end!),
    );

    if (!mounted) return;

    switch (result.outcome) {
      case ExportOutcome.success:
        ToastUtils.showSuccess(
          context,
          format == ExportFormat.receipts
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
    final bool isBusy = widget.state.isBusyFor(widget.kind);
    final bool isDisabled = widget.state.isBusy && !isBusy;
    final bool isInteractive = !isBusy && !isDisabled;

    final Color resting = widget.isOdd
        ? AppColors.TABLE_ROW_STRIPE
        : AppColors.SURFACE;
    final Color background = _isHovered && isInteractive
        ? AppColors.TABLE_ROW_HOVER
        : resting;

    final String? note = widget.kind.hasNoDateWindow
        ? AppStrings.EXPORT_WINDOW_NOT_APPLICABLE
        : (_isWindowOptional ? AppStrings.EXPORT_WINDOW_OPTIONAL : null);

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Opacity(
        opacity: isDisabled ? 0.45 : 1,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            color: background,
            border: const Border(
              bottom: BorderSide(color: AppColors.TABLE_ROW_DIVIDER),
            ),
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: AppSpacing.sm,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    Expanded(
                      flex: 5,
                      child: _RowIdentity(kind: widget.kind),
                    ),
                    SizedBox(
                      width: 340,
                      child: widget.kind.hasNoDateWindow
                          ? null
                          : Padding(
                              padding: const EdgeInsets.only(
                                right: AppSpacing.md,
                              ),
                              child: DateRangeField(
                                value: _rangeValue,
                                enabled: isInteractive,
                                presets: _presets,
                                onChanged: _onRangeChanged,
                              ),
                            ),
                    ),
                    SizedBox(
                      width: 140,
                      child: Align(
                        alignment: Alignment.centerRight,
                        child: _DownloadButton(
                          isBusy: isBusy,
                          isEnabled: isInteractive,
                          onTap: _onDownload,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              if (note != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.xs),
                  child: Text(
                    note,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_SECONDARY,
                    ),
                  ),
                ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpacing.xs),
                  child: Text(
                    _error!,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.ERROR,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RowIdentity extends StatelessWidget {
  final ExportKind kind;

  const _RowIdentity({required this.kind});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: AppSizes.exportIconTile,
          height: AppSizes.exportIconTile,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.PRIMARY_SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Icon(
            kind.icon,
            size: AppSizes.iconLg,
            color: AppColors.PRIMARY,
          ),
        ),
        const SizedBox(width: AppSpacing.smd),
        Flexible(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(kind.label, style: AppTypography.labelStrong),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                kind.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DownloadButton extends StatelessWidget {
  final bool isBusy;
  final bool isEnabled;
  final VoidCallback onTap;

  const _DownloadButton({
    required this.isBusy,
    required this.isEnabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    if (isBusy) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: AppSizes.iconSm,
            height: AppSizes.iconSm,
            child: CircularProgressIndicator(
              strokeWidth: AppSizes.borderMedium,
              color: AppColors.PRIMARY,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            AppStrings.EXPORT_BUILDING,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.PRIMARY_DARK,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
    }

    return MouseRegion(
      cursor: isEnabled
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      child: Material(
        color: AppColors.PRIMARY,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: InkWell(
          onTap: isEnabled ? onTap : null,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          child: const Padding(
            padding: EdgeInsets.symmetric(
              horizontal: AppSpacing.smd,
              vertical: AppSpacing.sm,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.download_rounded,
                  size: AppSizes.iconSm,
                  color: AppColors.TEXT_ON_PRIMARY,
                ),
                SizedBox(width: AppSpacing.xs),
                Text(
                  AppStrings.EXPORT,
                  style: TextStyle(
                    color: AppColors.TEXT_ON_PRIMARY,
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
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
