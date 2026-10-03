import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/product_thumbnail.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../products/data/models/product_model.dart';

/// One line on a custom order, held as a controller so the row survives
/// rebuilds while the user is typing.
///
/// Product and packet weight come from the picker rather than inline
/// dropdowns, so a line always names a packaging the product really has.
class CustomOrderLine {
  final ProductModel? product;
  final String productPublicId;
  final String productName;
  final String imageUrl;
  final String packetWeight;
  final int packetsPerBag;
  int packets;
  final TextEditingController price;

  CustomOrderLine({
    this.product,
    required this.productPublicId,
    required this.productName,
    this.imageUrl = '',
    required this.packetWeight,
    this.packetsPerBag = 0,
    this.packets = 1,
    String? priceText,
  }) : price = TextEditingController(text: priceText ?? '');

  void dispose() => price.dispose();

  /// Product and weight are fixed by the picker, so only the typed fields
  /// can still be wrong.
  bool get isValid =>
      productPublicId.isNotEmpty &&
      packetWeight.isNotEmpty &&
      packets > 0 &&
      (num.tryParse(price.text.trim()) ?? -1) >= 0;

  num get lineTotal => (num.tryParse(price.text.trim()) ?? 0) * packets;

  /// Identifies the line: the same product may appear at several weights.
  String get key => '$productPublicId|$packetWeight';

  Map<String, dynamic> toJson() => {
    'product_public_id': productPublicId,
    'packet_weight': packetWeight,
    'packets': packets,
    'negotiated_selling_price': price.text.trim(),
  };
}

class CustomOrderLineRow extends StatelessWidget {
  final CustomOrderLine line;
  final bool isEditable;
  final VoidCallback? onIncrement;
  final VoidCallback? onDecrement;
  final VoidCallback? onRemove;
  final ValueChanged<String>? onPriceChanged;

  const CustomOrderLineRow({
    super.key,
    required this.line,
    this.isEditable = false,
    this.onIncrement,
    this.onDecrement,
    this.onRemove,
    this.onPriceChanged,
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
            ProductThumbnail(url: line.imageUrl),
            const SizedBox(width: AppSpacing.smd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    line.productName,
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
                      _Chip(label: '${line.packetWeight} kg'),
                      if (line.packetsPerBag > 0)
                        _Chip(
                          label:
                              '${line.packetsPerBag} x ${line.packetWeight} kg',
                        ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            if (isEditable)
              _PacketStepper(
                packets: line.packets,
                onIncrement: onIncrement,
                onDecrement: onDecrement,
              )
            else
              _PacketPill(packets: line.packets),
            if (isEditable && onRemove != null) ...[
              const SizedBox(width: AppSpacing.sm),
              IconActionButton(
                icon: Icons.delete_outline_rounded,
                tooltip: AppStrings.ORDER_REMOVE_ITEM,
                type: IconActionType.error,
                onPressed: onRemove,
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            if (isEditable)
              SizedBox(
                width: AppSizes.orderPriceFieldWidth,
                child: AppTextField(
                  controller: line.price,
                  hint: AppStrings.FIELD_NEGOTIATED_PRICE_HINT,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  inputFormatters: [
                    FilteringTextInputFormatter.allow(
                      RegExp(r'^\d*\.?\d{0,2}'),
                    ),
                  ],
                  onChanged: onPriceChanged,
                ),
              )
            else
              Text(
                CurrencyFormatter.rupees(
                  num.tryParse(line.price.text.trim()) ?? 0,
                ),
                style: AppTypography.bodySmall,
              ),
            const SizedBox(width: AppSpacing.sm),
            Text(
              AppStrings.CUSTOM_ORDER_PER_PACKET,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
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

class _PacketStepper extends StatelessWidget {
  final int packets;
  final VoidCallback? onIncrement;
  final VoidCallback? onDecrement;

  const _PacketStepper({
    required this.packets,
    this.onIncrement,
    this.onDecrement,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconActionButton(icon: Icons.remove_rounded, onPressed: onDecrement),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
          child: Text('$packets', style: AppTypography.labelStrong),
        ),
        IconActionButton(icon: Icons.add_rounded, onPressed: onIncrement),
      ],
    );
  }
}

class _PacketPill extends StatelessWidget {
  final int packets;

  const _PacketPill({required this.packets});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.smd,
        vertical: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text('$packets', style: AppTypography.labelStrong),
    );
  }
}
