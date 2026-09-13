import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/dialogs/app_detail_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/feedback/form_step_indicator.dart';
import '../../../../core/widgets/feedback/image_viewer_dialog.dart';
import '../../data/models/product_model.dart';

class ProductDetailDialog extends StatefulWidget {
  final ProductModel product;

  const ProductDetailDialog({super.key, required this.product});

  static Future<void> show(BuildContext context, ProductModel product) {
    return showDialog<void>(
      context: context,
      builder: (_) => ProductDetailDialog(product: product),
    );
  }

  @override
  State<ProductDetailDialog> createState() => _ProductDetailDialogState();
}

class _ProductDetailDialogState extends State<ProductDetailDialog> {
  int _step = 0;

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.inventory_2_outlined,
      title: AppStrings.PRODUCT_DETAIL_TITLE,
      subtitle: AppStrings.PRODUCT_DETAIL_SUBTITLE,
      fixedHeight: AppSizes.detailDialogFixedHeight,
      footer: Row(
        children: [
          Expanded(
            child: SecondaryButton(
              label: AppStrings.STEP_BACK,
              onPressed: _step == 0
                  ? null
                  : () => setState(() => _step -= 1),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            flex: 2,
            child: PrimaryButton(
              label: _step == 2 ? AppStrings.CLOSE : AppStrings.STEP_NEXT,
              onPressed: _step == 2
                  ? () => Navigator.of(context).pop()
                  : () => setState(() => _step += 1),
            ),
          ),
        ],
      ),
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          FormStepIndicator(
            labels: const [
              AppStrings.PRODUCT_STEP_BASIC,
              AppStrings.PRODUCT_STEP_DETAILS,
              AppStrings.PRODUCT_STEP_IMAGE,
            ],
            currentIndex: _step,
            onStepTapped: (step) => setState(() => _step = step),
          ),
          const SizedBox(height: AppSpacing.lg),
          _buildStepBody(),
        ],
      ),
    );
  }

  Widget _buildStepBody() {
    switch (_step) {
      case 0:
        return _buildBasics();
      case 1:
        return _buildDetails();
      default:
        return _buildImage();
    }
  }

  Widget _buildBasics() {
    return DetailFieldGrid(
      fields: [
        DetailField(label: AppStrings.COLUMN_NAME, value: widget.product.name),
        DetailField(
          label: AppStrings.COLUMN_CROP,
          value: widget.product.cropName,
        ),
        DetailField(
          label: AppStrings.COLUMN_SELLING_PRICE,
          value: widget.product.sellingPrice,
        ),
      ],
    );
  }

  Widget _buildDetails() {
    final List<String> items = widget.product.descriptionItems;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        DetailFieldGrid(
          fields: [
            DetailField(
              label: AppStrings.COLUMN_STAGE,
              value: widget.product.stageName,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          AppStrings.PRODUCT_DESCRIPTION_LABEL,
          style: AppTypography.labelStrong,
        ),
        const SizedBox(height: AppSpacing.sm),
        if (items.isEmpty)
          Text(
            AppStrings.TABLE_VALUE_UNAVAILABLE,
            style: AppTypography.bodyMedium.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          )
        else
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xs),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('•  ', style: AppTypography.bodyMedium),
                  Expanded(child: Text(item, style: AppTypography.bodyMedium)),
                ],
              ),
            ),
      ],
    );
  }

  Widget _buildImage() {
    final String url = widget.product.imageDisplayUrl;

    if (url.isEmpty) return _imageFrame(child: _buildPlaceholder());

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MouseRegion(
          cursor: SystemMouseCursors.zoomIn,
          child: GestureDetector(
            onTap: () => ImageViewerDialog.show(
              context,
              url: url,
              title: widget.product.name,
            ),
            child: _imageFrame(
              child: Image.network(
                url,
                fit: BoxFit.contain,
                errorBuilder: (context, error, stack) => _buildPlaceholder(),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          AppStrings.IMAGE_VIEW_HINT,
          textAlign: TextAlign.center,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      ],
    );
  }

  Widget _imageFrame({required Widget child}) {
    return Container(
      height: AppSizes.productImagePreview,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }

  Widget _buildPlaceholder() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(
          Icons.image_outlined,
          size: AppSizes.iconXl,
          color: AppColors.TEXT_DISABLED,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          AppStrings.PRODUCT_IMAGE_EMPTY,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
        ),
      ],
    );
  }
}
