import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../../features/products/data/models/product_model.dart';
import 'searchable_popup_menu.dart';

class ProductPickerField extends StatelessWidget {
  final ProductModel? value;
  final List<ProductModel> products;
  final ValueChanged<ProductModel> onSelected;
  final String? errorText;
  final bool enabled;
  final bool isUnavailable;

  const ProductPickerField({
    super.key,
    required this.value,
    required this.products,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.isUnavailable = false,
  });

  static String label(ProductModel product) => product.name;

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
    final bool hasError = errorText != null && errorText!.isNotEmpty;

    final Widget field = Container(
      height: AppSizes.inputHeight,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      decoration: BoxDecoration(
        color: enabled ? AppColors.SURFACE : AppColors.SURFACE_VARIANT,
        border: Border.all(
          color: hasError ? AppColors.ERROR : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              value == null ? AppStrings.FIELD_PRODUCT_HINT : label(value!),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.bodyMedium.copyWith(
                color: value == null
                    ? AppColors.TEXT_DISABLED
                    : AppColors.TEXT_PRIMARY,
              ),
            ),
          ),
          const Icon(
            Icons.keyboard_arrow_down_rounded,
            size: AppSizes.iconMd,
            color: AppColors.TEXT_SECONDARY,
          ),
        ],
      ),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(AppStrings.FIELD_PRODUCT, style: AppTypography.labelStrong),
        const SizedBox(height: AppSpacing.sm),
        if (enabled)
          SearchablePopupMenu<ProductModel>(
            items: products,
            itemToString: label,
            optionsBuilder: (query) =>
                optionsFor(products: products, query: query),
            isSelected: (product) => product.publicId == value?.publicId,
            onSelected: onSelected,
            child: field,
          )
        else
          field,
        if (isUnavailable) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.PRODUCTS_UNAVAILABLE,
            style: AppTypography.caption.copyWith(color: AppColors.WARNING),
          ),
        ],
        if (hasError) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            errorText!,
            style: AppTypography.caption.copyWith(color: AppColors.ERROR),
          ),
        ],
      ],
    );
  }
}
