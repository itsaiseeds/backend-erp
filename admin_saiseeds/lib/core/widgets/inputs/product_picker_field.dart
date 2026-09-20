import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../../features/products/data/models/product_model.dart';
import 'searchable_field.dart';

class ProductPickerField extends StatelessWidget {
  final ProductModel? value;
  final List<ProductModel> products;
  final ValueChanged<ProductModel> onSelected;
  final String? errorText;
  final bool enabled;
  final VoidCallback? onBlockedTap;
  final bool isUnavailable;

  const ProductPickerField({
    super.key,
    required this.value,
    required this.products,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.onBlockedTap,
    this.isUnavailable = false,
  });

  static String label(ProductModel product) => product.name;

  static String searchText(ProductModel product) =>
      '${product.name} ${product.cropName}';

  static List<ProductModel> optionsFor({
    required List<ProductModel> products,
    required String query,
  }) {
    final String needle = query.trim().toLowerCase();
    if (needle.isEmpty) return List<ProductModel>.from(products);

    return products
        .where(
          (product) =>
              product.name.toLowerCase().contains(needle) ||
              product.cropName.toLowerCase().contains(needle),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    return SearchableField<ProductModel>(
      label: AppStrings.FIELD_PRODUCT,
      hintText: AppStrings.FIELD_PRODUCT_HINT,
      value: value,
      items: products,
      itemToString: label,
      searchText: searchText,
      isSame: (a, b) => a.publicId == b.publicId,
      onSelected: onSelected,
      errorText: errorText,
      enabled: enabled,
      onBlockedTap: onBlockedTap,
      helperText: isUnavailable ? AppStrings.PRODUCTS_UNAVAILABLE : null,
      emptyHint: AppStrings.PRODUCTS_UNAVAILABLE,
    );
  }
}
