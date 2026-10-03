import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../services/packagings_service.dart';
import 'searchable_field.dart';

/// Picks one of the packet weights configured for a product.
///
/// The weights come from the product's packagings rather than free text, so
/// an order can only ask for a size the product is actually packed in. With
/// no product chosen yet the field stays disabled and says so.
class PacketWeightPickerField extends StatelessWidget {
  final String? productPublicId;
  final String? value;
  final ValueChanged<String> onSelected;
  final String? errorText;
  final bool enabled;

  const PacketWeightPickerField({
    super.key,
    required this.productPublicId,
    required this.value,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
  });

  static String label(String weight) => weight;

  @override
  Widget build(BuildContext context) {
    final String product = productPublicId ?? '';
    final List<String> weights = PackagingsService.instance.packetWeightsFor(
      product,
    );

    final bool hasProduct = product.isNotEmpty;
    final String? helper = !hasProduct
        ? AppStrings.FIELD_PACKET_WEIGHT_PICK_PRODUCT
        : (weights.isEmpty ? AppStrings.FIELD_PACKET_WEIGHT_NONE : null);

    return SearchableField<String>(
      label: AppStrings.FIELD_PACKET_WEIGHT_SELECT,
      hintText: AppStrings.FIELD_PACKET_WEIGHT_SELECT_HINT,
      value: weights.contains(value) ? value : null,
      items: weights,
      itemToString: label,
      isSame: (a, b) => a == b,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled && hasProduct && weights.isNotEmpty,
      helperText: helper,
      emptyHint: AppStrings.FIELD_PACKET_WEIGHT_NONE,
    );
  }
}
