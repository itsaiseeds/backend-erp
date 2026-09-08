import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/widgets/dialogs/app_detail_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../data/models/product_packaging_model.dart';

class ProductPackagingDetailDialog extends StatelessWidget {
  final ProductPackagingModel packaging;

  const ProductPackagingDetailDialog({super.key, required this.packaging});

  static Future<void> show(
    BuildContext context,
    ProductPackagingModel packaging,
  ) {
    return showDialog<void>(
      context: context,
      builder: (_) => ProductPackagingDetailDialog(packaging: packaging),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.inventory_outlined,
      title: AppStrings.PRODUCT_PACKAGING_DETAIL_TITLE,
      subtitle: AppStrings.PRODUCT_PACKAGING_DETAIL_SUBTITLE,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          DetailFieldGrid(
            fields: [
              DetailField(
                label: AppStrings.COLUMN_PRODUCT,
                value: packaging.productName,
              ),
              DetailField(
                label: AppStrings.COLUMN_PACKET_WEIGHT,
                value: packaging.packetWeight,
              ),
              DetailField(
                label: AppStrings.COLUMN_PACKETS,
                value: packaging.packetsLabel,
              ),
              DetailField(
                label: AppStrings.COLUMN_TOTAL_WEIGHT,
                value: packaging.totalWeight,
              ),
              DetailField(
                label: AppStrings.COLUMN_SELLING_PRICE,
                value: packaging.sellingPrice,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
