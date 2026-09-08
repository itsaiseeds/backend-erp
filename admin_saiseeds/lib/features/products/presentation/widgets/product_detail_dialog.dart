import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/widgets/dialogs/app_detail_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../data/models/product_model.dart';

class ProductDetailDialog extends StatelessWidget {
  final ProductModel product;

  const ProductDetailDialog({super.key, required this.product});

  static Future<void> show(BuildContext context, ProductModel product) {
    return showDialog<void>(
      context: context,
      builder: (_) => ProductDetailDialog(product: product),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.inventory_2_outlined,
      title: AppStrings.PRODUCT_DETAIL_TITLE,
      subtitle: AppStrings.PRODUCT_DETAIL_SUBTITLE,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          DetailFieldGrid(
            fields: [
              DetailField(label: AppStrings.COLUMN_NAME, value: product.name),
              DetailField(
                label: AppStrings.COLUMN_CROP,
                value: product.cropName,
              ),
              DetailField(
                label: AppStrings.COLUMN_BUYING_PRICE,
                value: product.buyingPrice,
              ),
              DetailField(
                label: AppStrings.COLUMN_SELLING_PRICE,
                value: product.sellingPrice,
              ),
              DetailField(
                label: AppStrings.COLUMN_MARGIN_PER_PACKET,
                value: product.marginPerPacket,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
