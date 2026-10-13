import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_dialog_shell.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../data/models/rejected_lot_model.dart';

/// Opened by "Add lot" -- lets the admin tick off any number of the farmer's
/// rejected lots in one pass instead of re-opening the picker per lot.
/// Selected cards stay highlighted and sit at the top of the list, and a
/// search field narrows a long lot list down by product or lot number.
class RejectedLotPickerDialog extends StatefulWidget {
  final List<RejectedLotModel> lots;

  const RejectedLotPickerDialog({super.key, required this.lots});

  /// Resolves to `null` if cancelled, or the picked lots (possibly empty is
  /// never returned -- "Add" is disabled until at least one is ticked).
  static Future<List<RejectedLotModel>?> show(
    BuildContext context, {
    required List<RejectedLotModel> lots,
  }) {
    return showDialog<List<RejectedLotModel>>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (_) => RejectedLotPickerDialog(lots: lots),
    );
  }

  @override
  State<RejectedLotPickerDialog> createState() =>
      _RejectedLotPickerDialogState();
}

class _RejectedLotPickerDialogState extends State<RejectedLotPickerDialog> {
  final TextEditingController _searchController = TextEditingController();
  final Set<String> _selected = {};
  String _query = '';

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<RejectedLotModel> get _filtered {
    final String needle = _query.trim().toLowerCase();
    if (needle.isEmpty) return widget.lots;
    return widget.lots
        .where(
          (lot) =>
              lot.productName.toLowerCase().contains(needle) ||
              lot.lotNo.toLowerCase().contains(needle),
        )
        .toList();
  }

  void _toggle(RejectedLotModel lot) {
    setState(() {
      final String key = lot.inwardRawMaterialPublicId;
      if (!_selected.add(key)) _selected.remove(key);
    });
  }

  void _submit() {
    final List<RejectedLotModel> picked = widget.lots
        .where((lot) => _selected.contains(lot.inwardRawMaterialPublicId))
        .toList();
    Navigator.of(context).pop(picked);
  }

  @override
  Widget build(BuildContext context) {
    final List<RejectedLotModel> visible = _filtered;
    final int count = _selected.length;

    return AppDialogShell(
      title: AppStrings.FIELD_REJECTED_LOT,
      subtitle: count == 0
          ? AppStrings.REJECTED_LOT_PICKER_SUBTITLE
          : AppStrings.REJECTED_LOT_PICKER_SELECTED_COUNT.replaceAll(
              '%n',
              '$count',
            ),
      tone: DialogHeaderTone.primary,
      icon: Icons.inventory_2_outlined,
      width: AppSizes.rejectedLotPickerWidth,
      content: SizedBox(
        height: AppSizes.rejectedLotPickerHeight,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            AppTextField(
              controller: _searchController,
              hint: AppStrings.REJECTED_LOT_PICKER_SEARCH_HINT,
              prefixIcon: Icons.search_rounded,
              onChanged: (value) => setState(() => _query = value),
            ),
            const SizedBox(height: AppSpacing.md),
            Expanded(
              child: widget.lots.isEmpty
                  ? _EmptyState(message: AppStrings.REJECTED_LOTS_UNAVAILABLE)
                  : visible.isEmpty
                  ? _EmptyState(message: AppStrings.NO_RESULTS_FOUND)
                  : ListView.separated(
                      itemCount: visible.length,
                      separatorBuilder: (_, _) =>
                          const SizedBox(height: AppSpacing.sm),
                      itemBuilder: (context, index) {
                        final RejectedLotModel lot = visible[index];
                        return _LotCard(
                          lot: lot,
                          isSelected: _selected.contains(
                            lot.inwardRawMaterialPublicId,
                          ),
                          onTap: () => _toggle(lot),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      actions: [
        SecondaryButton(
          label: AppStrings.CANCEL,
          onPressed: () => Navigator.of(context).pop(),
        ),
        PrimaryButton(
          label: count == 0
              ? AppStrings.REJECTED_LOT_ORDER_ADD_LOT
              : AppStrings.REJECTED_LOT_PICKER_ADD_COUNT.replaceAll(
                  '%n',
                  '$count',
                ),
          onPressed: count == 0 ? null : _submit,
        ),
      ],
    );
  }
}

class _LotCard extends StatelessWidget {
  final RejectedLotModel lot;
  final bool isSelected;
  final VoidCallback onTap;

  const _LotCard({
    required this.lot,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          padding: const EdgeInsets.all(AppSpacing.smd),
          decoration: BoxDecoration(
            color: isSelected ? AppColors.PRIMARY_SURFACE : AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.md),
            border: Border.all(
              color: isSelected ? AppColors.PRIMARY : AppColors.BORDER,
              width: isSelected ? AppSizes.borderMedium : AppSizes.borderThin,
            ),
          ),
          child: Row(
            children: [
              _SelectionMark(isSelected: isSelected),
              const SizedBox(width: AppSpacing.smd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      lot.productName,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.bodyMedium.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.xxs),
                    Wrap(
                      spacing: AppSpacing.xs,
                      runSpacing: AppSpacing.xs,
                      children: [
                        _Chip(label: lot.lotNo, isSelected: isSelected),
                        _Chip(
                          label:
                              '${lot.remainingKg} '
                              '${AppStrings.REJECTED_LOT_REMAINING_SUFFIX}',
                          isSelected: isSelected,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SelectionMark extends StatelessWidget {
  final bool isSelected;

  const _SelectionMark({required this.isSelected});

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 120),
      width: AppSizes.iconLg,
      height: AppSizes.iconLg,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: isSelected ? AppColors.PRIMARY : AppColors.TRANSPARENT,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(
          color: isSelected ? AppColors.PRIMARY : AppColors.BORDER_STRONG,
          width: AppSizes.borderMedium,
        ),
      ),
      child: isSelected
          ? const Icon(
              Icons.check_rounded,
              size: AppSizes.iconSm,
              color: AppColors.WHITE,
            )
          : null,
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  final bool isSelected;

  const _Chip({required this.label, required this.isSelected});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: isSelected ? AppColors.SURFACE : AppColors.SURFACE_VARIANT,
        border: Border.all(
          color: isSelected ? AppColors.PRIMARY : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        style: AppTypography.bodySmall.copyWith(color: AppColors.TEXT_PRIMARY),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String message;

  const _EmptyState({required this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        message,
        style: AppTypography.bodySmall.copyWith(color: AppColors.TEXT_SECONDARY),
      ),
    );
  }
}
