import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../products/data/models/product_model.dart';

/// One line on a waste order, held as controllers so the row survives
/// rebuilds while the user is typing.
///
/// Unlike a packet order's line, there is no packaging to pick -- waste is
/// sold by the kilogram at whatever price per kg the admin negotiates, so
/// both [quantityKg] and [price] are free-typed. The product itself is also
/// picked right on the row rather than through a separate dialog, so a blank
/// line (no product yet) is a valid starting state, not an error.
class WasteOrderLine {
  ProductModel? product;
  String productPublicId;
  String productName;
  String imageUrl;
  final TextEditingController quantityKg;
  final TextEditingController price;

  WasteOrderLine({
    this.product,
    this.productPublicId = '',
    this.productName = '',
    this.imageUrl = '',
    String? quantityKgText,
    String? priceText,
  }) : quantityKg = TextEditingController(text: quantityKgText ?? ''),
       price = TextEditingController(text: priceText ?? '');

  void dispose() {
    quantityKg.dispose();
    price.dispose();
  }

  bool get isValid =>
      productPublicId.isNotEmpty &&
      (num.tryParse(quantityKg.text.trim()) ?? -1) > 0 &&
      (num.tryParse(price.text.trim()) ?? -1) >= 0;

  num get lineTotal =>
      (num.tryParse(price.text.trim()) ?? 0) *
      (num.tryParse(quantityKg.text.trim()) ?? 0);

  /// Identifies the line: one line per product, kilograms combine rather than
  /// a product appearing twice.
  String get key => productPublicId;

  Map<String, dynamic> toJson() => {
    'product_public_id': productPublicId,
    'quantity_kg': quantityKg.text.trim(),
    'negotiated_selling_price': price.text.trim(),
  };
}

/// A single inline row: product, kg, price, a running total and a remove
/// button -- everything needed to add one line, with no separate dialog.
class WasteOrderLineRow extends StatelessWidget {
  final WasteOrderLine line;
  final List<ProductModel> products;
  final bool isEditable;
  final VoidCallback? onRemove;
  final VoidCallback? onChanged;

  const WasteOrderLineRow({
    super.key,
    required this.line,
    required this.products,
    this.isEditable = false,
    this.onRemove,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    if (!isEditable) return _buildReadOnly();

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          flex: 3,
          child: ProductPickerField(
            value: line.product,
            products: products,
            onSelected: (product) {
              line.product = product;
              line.productPublicId = product.publicId;
              line.productName = product.name;
              line.imageUrl = product.imageUrl;
              onChanged?.call();
            },
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 2,
          child: AppTextField(
            controller: line.quantityKg,
            label: AppStrings.WASTE_ORDER_FIELD_QUANTITY_KG,
            hint: AppStrings.WASTE_ORDER_FIELD_QUANTITY_KG_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,3}')),
            ],
            onChanged: (_) => onChanged?.call(),
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 2,
          child: AppTextField(
            controller: line.price,
            label: AppStrings.WASTE_ORDER_FIELD_PRICE_PER_KG,
            hint: AppStrings.FIELD_NEGOTIATED_PRICE_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'^\d*\.?\d{0,2}')),
            ],
            onChanged: (_) => onChanged?.call(),
          ),
        ),
        if (onRemove != null) ...[
          const SizedBox(width: AppSpacing.sm),
          Padding(
            padding: const EdgeInsets.only(top: AppSpacing.lg),
            child: IconActionButton(
              icon: Icons.close_rounded,
              tooltip: AppStrings.ORDER_REMOVE_ITEM,
              type: IconActionType.error,
              onPressed: onRemove,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildReadOnly() {
    return Row(
      children: [
        Expanded(
          flex: 3,
          child: Text(
            line.productName,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 2,
          child: Text(
            '${line.quantityKg.text.trim()} kg',
            style: AppTypography.bodyMedium,
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 2,
          child: Text(
            CurrencyFormatter.rupees(num.tryParse(line.price.text.trim()) ?? 0),
            style: AppTypography.bodyMedium,
          ),
        ),
        const SizedBox(width: AppSpacing.sm),
        Expanded(
          flex: 2,
          child: Text(
            CurrencyFormatter.rupees(line.lineTotal),
            textAlign: TextAlign.right,
            style: AppTypography.labelStrong.copyWith(
              color: AppColors.PRIMARY_DARK,
            ),
          ),
        ),
      ],
    );
  }
}
