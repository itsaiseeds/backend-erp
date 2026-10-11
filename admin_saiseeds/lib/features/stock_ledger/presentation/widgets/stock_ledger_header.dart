import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../products/data/models/product_model.dart';
import '../bloc/stock_ledger_cubit.dart';
import '../bloc/stock_ledger_state.dart';

/// The top bar: product + date-range pickers, the Load action (which turns
/// into a disabled countdown once the daily build quota is spent), the
/// builds-remaining pips and the "loaded from cache" note.
class StockLedgerHeader extends StatefulWidget {
  const StockLedgerHeader({super.key});

  @override
  State<StockLedgerHeader> createState() => _StockLedgerHeaderState();
}

class _StockLedgerHeaderState extends State<StockLedgerHeader> {
  Timer? _ticker;

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  void _ensureTicking(bool shouldTick) {
    if (shouldTick && _ticker == null) {
      _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() {});
      });
    } else if (!shouldTick && _ticker != null) {
      _ticker?.cancel();
      _ticker = null;
    }
  }

  void _pickQuickRange(StockLedgerCubit cubit, int daysBack) {
    final DateTime today = DateTime.now();
    final DateTime todayOnly = DateTime(today.year, today.month, today.day);
    final DateTime start = todayOnly.subtract(Duration(days: daysBack));
    cubit.setDateRange(start, todayOnly);
  }

  void _pickThisMonth(StockLedgerCubit cubit) {
    final DateTime today = DateTime.now();
    final DateTime todayOnly = DateTime(today.year, today.month, today.day);
    final DateTime start = DateTime(today.year, today.month, 1);
    cubit.setDateRange(start, todayOnly);
  }

  String _formatCountdown(Duration d) {
    final int total = d.inSeconds.clamp(0, 24 * 3600);
    final int h = total ~/ 3600;
    final int m = (total % 3600) ~/ 60;
    final int s = total % 60;
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(h)}:${two(m)}:${two(s)}';
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<StockLedgerCubit, StockLedgerState>(
      builder: (context, state) {
        final StockLedgerCubit cubit = context.read<StockLedgerCubit>();
        final bool isRateLimited =
            state.status == StockLedgerStatus.rateLimited &&
            state.rateLimitedUntil != null &&
            state.rateLimitedUntil!.isAfter(DateTime.now());
        _ensureTicking(isRateLimited);

        return Container(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            AppSpacing.smd,
            AppSpacing.lg,
            AppSpacing.smd,
          ),
          decoration: const BoxDecoration(
            color: AppColors.SURFACE,
            border: Border(bottom: BorderSide(color: AppColors.BORDER)),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            physics: const ClampingScrollPhysics(),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                _Brand(),
                const SizedBox(width: AppSpacing.md),
                Container(width: 1, height: 36, color: AppColors.BORDER),
                const SizedBox(width: AppSpacing.md),
                _ProductPicker(cubit: cubit, state: state),
                const SizedBox(width: AppSpacing.md),
                _DateRangeField(cubit: cubit, state: state),
                const SizedBox(width: AppSpacing.smd),
                _QuickRangeButtons(
                  state: state,
                  onToday: () => _pickQuickRange(cubit, 0),
                  onLast7: () => _pickQuickRange(cubit, 6),
                  onThisMonth: () => _pickThisMonth(cubit),
                ),
                const SizedBox(width: AppSpacing.md),
                _LoadAction(
                  cubit: cubit,
                  state: state,
                  isRateLimited: isRateLimited,
                  countdownText: isRateLimited
                      ? _formatCountdown(
                          state.rateLimitedUntil!.difference(DateTime.now()),
                        )
                      : '',
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _Brand extends StatelessWidget {
  // Matches the label + gap + 36px input stack height of the sibling
  // fields in this row, so the brand block can center within the same
  // footprint instead of sharing the row's bottom (CrossAxisAlignment.end)
  // alignment with them.
  static const double _siblingFieldHeight = 60;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: _siblingFieldHeight,
      child: Align(
        alignment: Alignment.center,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 30,
              height: 30,
              decoration: BoxDecoration(
                color: AppColors.PRIMARY,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              alignment: Alignment.center,
              child: const Icon(
                Icons.link_rounded,
                size: 18,
                color: AppColors.TEXT_ON_PRIMARY,
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.STOCK_LEDGER_HEADER_EYEBROW,
                  style: AppTypography.bodySmall,
                ),
                Text(
                  AppStrings.STOCK_LEDGER_SUBTITLE,
                  style: AppTypography.titleMedium.copyWith(fontSize: 15),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ProductPicker extends StatelessWidget {
  final StockLedgerCubit cubit;
  final StockLedgerState state;

  const _ProductPicker({required this.cubit, required this.state});

  @override
  Widget build(BuildContext context) {
    final ProductModel? value = state.productPublicId == null
        ? null
        : ProductsService.instance.productByPublicId(state.productPublicId!);

    return SizedBox(
      width: 270,
      child: ProductPickerField(
        value: value,
        products: ProductsService.instance.products,
        onSelected: (product) => cubit.selectProduct(
          publicId: product.publicId,
          name: product.name,
        ),
      ),
    );
  }
}

class _DateRangeField extends StatelessWidget {
  final StockLedgerCubit cubit;
  final StockLedgerState state;

  const _DateRangeField({required this.cubit, required this.state});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.STOCK_LEDGER_DATE_RANGE_LABEL,
          style: AppTypography.labelStrong,
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 150,
              child: SingleDateField(
                value: state.startDate,
                onChanged: (date) {
                  if (date == null) return;
                  final DateTime end =
                      state.endDate != null && state.endDate!.isBefore(date)
                      ? date
                      : (state.endDate ?? date);
                  cubit.setDateRange(date, end);
                },
              ),
            ),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: AppSpacing.xs),
              child: Icon(
                Icons.arrow_forward_rounded,
                size: 16,
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
            SizedBox(
              width: 150,
              child: SingleDateField(
                value: state.endDate,
                onChanged: (date) {
                  if (date == null) return;
                  final DateTime start =
                      state.startDate != null && state.startDate!.isAfter(date)
                      ? date
                      : (state.startDate ?? date);
                  cubit.setDateRange(start, date);
                },
              ),
            ),
          ],
        ),
        if (state.goLiveError != null)
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.xs),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.error_outline_rounded,
                  size: 14,
                  color: AppColors.ERROR,
                ),
                const SizedBox(width: AppSpacing.xs),
                Text(
                  state.goLiveError!,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.ERROR,
                    fontSize: 11.5,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

enum _QuickRange { today, last7, thisMonth }

class _QuickRangeButtons extends StatelessWidget {
  final StockLedgerState state;
  final VoidCallback onToday;
  final VoidCallback onLast7;
  final VoidCallback onThisMonth;

  const _QuickRangeButtons({
    required this.state,
    required this.onToday,
    required this.onLast7,
    required this.onThisMonth,
  });

  static bool _isSameDay(DateTime? a, DateTime b) =>
      a != null && a.year == b.year && a.month == b.month && a.day == b.day;

  _QuickRange? get _active {
    final DateTime? start = state.startDate;
    final DateTime? end = state.endDate;
    if (start == null || end == null) return null;

    final DateTime today = DateTime.now();
    final DateTime todayOnly = DateTime(today.year, today.month, today.day);
    if (!_isSameDay(end, todayOnly)) return null;

    if (_isSameDay(start, todayOnly)) return _QuickRange.today;
    if (_isSameDay(start, todayOnly.subtract(const Duration(days: 6)))) {
      return _QuickRange.last7;
    }
    if (_isSameDay(start, DateTime(today.year, today.month, 1))) {
      return _QuickRange.thisMonth;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final _QuickRange? active = _active;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _QuickChip(
          label: AppStrings.STOCK_LEDGER_QUICK_TODAY,
          isActive: active == _QuickRange.today,
          onTap: onToday,
        ),
        const SizedBox(width: AppSpacing.xs),
        _QuickChip(
          label: AppStrings.STOCK_LEDGER_QUICK_LAST_7_DAYS,
          isActive: active == _QuickRange.last7,
          onTap: onLast7,
        ),
        const SizedBox(width: AppSpacing.xs),
        _QuickChip(
          label: AppStrings.STOCK_LEDGER_QUICK_THIS_MONTH,
          isActive: active == _QuickRange.thisMonth,
          onTap: onThisMonth,
        ),
      ],
    );
  }
}

class _QuickChip extends StatelessWidget {
  final String label;
  final bool isActive;
  final VoidCallback onTap;

  const _QuickChip({
    required this.label,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Material(
      color: isActive ? AppColors.PRIMARY.withValues(alpha: 0.08) : AppColors.SURFACE,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
          decoration: BoxDecoration(
            border: Border.all(
              color: isActive ? AppColors.PRIMARY : AppColors.BORDER,
            ),
            borderRadius: BorderRadius.circular(999),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: isActive ? AppColors.PRIMARY : AppColors.TEXT_PRIMARY,
              fontSize: 12.5,
              fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}

class _LoadAction extends StatelessWidget {
  final StockLedgerCubit cubit;
  final StockLedgerState state;
  final bool isRateLimited;
  final String countdownText;

  const _LoadAction({
    required this.cubit,
    required this.state,
    required this.isRateLimited,
    required this.countdownText,
  });

  @override
  Widget build(BuildContext context) {
    if (isRateLimited) {
      return Container(
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
        decoration: BoxDecoration(
          color: AppColors.SURFACE_VARIANT,
          border: Border.all(color: AppColors.BORDER),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.schedule_rounded,
              size: 17,
              color: AppColors.TEXT_SECONDARY,
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              AppStrings.STOCK_LEDGER_AVAILABLE_IN,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: AppSpacing.xs),
            Text(
              countdownText,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
      );
    }

    final bool canLoad =
        state.productPublicId != null &&
        state.startDate != null &&
        state.endDate != null &&
        state.status != StockLedgerStatus.loading;

    return Material(
      color: canLoad ? AppColors.PRIMARY : AppColors.PRIMARY.withValues(alpha: 0.5),
      borderRadius: BorderRadius.circular(AppRadius.md),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.md),
        onTap: canLoad ? () => cubit.loadLedger() : null,
        child: Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          alignment: Alignment.center,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (state.status == StockLedgerStatus.loading)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: AppColors.TEXT_ON_PRIMARY,
                  ),
                )
              else
                const Icon(
                  Icons.play_arrow_rounded,
                  size: 18,
                  color: AppColors.TEXT_ON_PRIMARY,
                ),
              const SizedBox(width: AppSpacing.xs),
              Text(
                AppStrings.STOCK_LEDGER_LOAD,
                style: AppTypography.button.copyWith(
                  color: AppColors.TEXT_ON_PRIMARY,
                  fontSize: 13.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

