import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../data/models/rejected_lot_model.dart';

/// One picked rejected lot on the order, held as controllers so the row
/// survives rebuilds while the user is typing.
///
/// [maxQuantityKg] caps what the quantity field accepts client-side -- the
/// server re-validates against its own live remaining figure regardless.
class RejectedLotOrderLine {
  final RejectedLotModel lot;
  final TextEditingController quantity;
  final TextEditingController price;
  final TextEditingController lotNumber;

  RejectedLotOrderLine({required this.lot})
    : quantity = TextEditingController(text: lot.remainingKg),
      price = TextEditingController(),
      lotNumber = TextEditingController(text: lot.lotNo);

  void dispose() {
    quantity.dispose();
    price.dispose();
    lotNumber.dispose();
  }

  num get maxQuantityKg => lot.remainingKgValue;

  /// Identifies the line -- the same farmer may have more than one rejected
  /// lot for the same product, so the raw material's own id is the key.
  String get key => lot.inwardRawMaterialPublicId;

  bool get isValid {
    final num? qty = num.tryParse(quantity.text.trim());
    final num? priceValue = num.tryParse(price.text.trim());
    return qty != null && qty > 0 && priceValue != null && priceValue >= 0;
  }

  num get lineTotal =>
      (num.tryParse(price.text.trim()) ?? 0) *
      (num.tryParse(quantity.text.trim()) ?? 0);

  Map<String, dynamic> toJson() => {
    'inward_raw_material_public_id': lot.inwardRawMaterialPublicId,
    'quantity_kg': quantity.text.trim(),
    'negotiated_selling_price': price.text.trim(),
    'lot_number': lotNumber.text.trim(),
  };
}

class RejectedLotOrderLineRow extends StatelessWidget {
  final RejectedLotOrderLine line;
  final VoidCallback? onRemove;
  final VoidCallback? onChanged;

  const RejectedLotOrderLineRow({
    super.key,
    required this.line,
    this.onRemove,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    line.lot.productName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: AppSpacing.xs,
                    children: [
                      _Chip(label: line.lot.farmerName),
                      _Chip(
                        label:
                            '${line.lot.remainingKg} '
                            '${AppStrings.REJECTED_LOT_REMAINING_SUFFIX}',
                      ),
                    ],
                  ),
                ],
              ),
            ),
            if (onRemove != null) ...[
              const SizedBox(width: AppSpacing.sm),
              IconActionButton(
                icon: Icons.delete_outline_rounded,
                tooltip: AppStrings.REJECTED_LOT_ORDER_REMOVE_LOT,
                type: IconActionType.error,
                onPressed: onRemove,
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: AppTextField(
                controller: line.lotNumber,
                label: AppStrings.FIELD_LOT_NUMBER_OVERRIDE,
                hint: AppStrings.FIELD_LOT_NUMBER_OVERRIDE_HINT,
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: AppTextField(
                controller: line.quantity,
                label: AppStrings.WASTE_ORDER_FIELD_QUANTITY_KG,
                hint: AppStrings.WASTE_ORDER_FIELD_QUANTITY_KG_HINT,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
                ],
                onChanged: (_) => onChanged?.call(),
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: AppTextField(
                controller: line.price,
                label: AppStrings.WASTE_ORDER_FIELD_PRICE_PER_KG,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
                ],
                onChanged: (_) => onChanged?.call(),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            const Spacer(),
            Text(
              CurrencyFormatter.rupees(line.lineTotal),
              style: AppTypography.labelStrong.copyWith(
                color: AppColors.PRIMARY_DARK,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;

  const _Chip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(color: AppColors.PRIMARY),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        style: AppTypography.bodySmall.copyWith(color: AppColors.TEXT_PRIMARY),
      ),
    );
  }
}
