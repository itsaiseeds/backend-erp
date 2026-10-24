import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/image_viewer_dialog.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../../products/data/models/product_model.dart';
import '../../data/models/product_packaging_model.dart';
import '../bloc/product_packagings_cubit.dart';
import 'selling_price_autofill.dart';

class ProductPackagingRecordDialog extends StatefulWidget {
  final ProductPackagingModel packaging;
  final RecordDialogMode initialMode;

  const ProductPackagingRecordDialog({
    super.key,
    required this.packaging,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    ProductPackagingModel packaging, {
    required ProductPackagingsCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<ProductPackagingsCubit>.value(
        value: cubit,
        child: ProductPackagingRecordDialog(
          packaging: packaging,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<ProductPackagingRecordDialog> createState() =>
      _ProductPackagingRecordDialogState();
}

class _ProductPackagingRecordDialogState
    extends State<ProductPackagingRecordDialog> {
  static final RegExp _pricePattern = RegExp(r'^\d*\.?\d{0,2}$');
  static final RegExp _decimalCharacters = RegExp(r'[0-9.]');

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final SellingPriceAutofill _autofill = SellingPriceAutofill();

  late final TextEditingController _packetWeightController;
  late final TextEditingController _packetsController;
  late final TextEditingController _sellingPriceController;
  late final TextEditingController _totalWeightController;

  late RecordDialogMode _mode;

  List<ProductModel> _products = const [];
  ProductModel? _selectedProduct;
  ProductPackagingImageUpload? _pickedImage;
  bool _imageRemoved = false;
  bool _isSubmitting = false;
  bool _areProductsUnavailable = false;

  ProductPackagingModel get _packaging => widget.packaging;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _packetWeightController = TextEditingController(
      text: _packaging.packetWeight,
    );
    _packetsController = TextEditingController(text: _packaging.packetsLabel);
    _sellingPriceController = TextEditingController(
      text: _packaging.sellingPrice,
    );
    _totalWeightController = TextEditingController(
      text: _packaging.totalWeight,
    );

    _autofill.adoptExistingValue(_sellingPriceController.text);
    _products = ProductsService.instance.products;
    _selectedProduct = _resolveSelectedProduct();
    _packetsController.addListener(_onInputChanged);
    _packetWeightController.addListener(_onInputChanged);
    _loadProducts();
  }

  @override
  void dispose() {
    _packetsController.removeListener(_onInputChanged);
    _packetWeightController.removeListener(_onInputChanged);
    _packetWeightController.dispose();
    _packetsController.dispose();
    _sellingPriceController.dispose();
    _totalWeightController.dispose();
    super.dispose();
  }

  ProductModel? _resolveSelectedProduct() {
    final String publicId = _packaging.productPublicId;
    if (publicId.isEmpty) return null;
    return ProductsService.instance.productByPublicId(publicId);
  }

  Future<void> _loadProducts() async {
    final bool succeeded = await ProductsService.instance.loadProducts();
    if (!mounted) return;
    setState(() {
      _products = ProductsService.instance.products;
      _areProductsUnavailable = !succeeded;
      _selectedProduct ??= _resolveSelectedProduct();
    });
  }

  void _onInputChanged() {
    if (!_isEditing) return;
    _applyAutofill();
    _recomputeTotalWeight();
  }

  /// Total weight is packets x packet weight; showing the fetched figure after
  /// either input changes would state a total the record no longer has.
  void _recomputeTotalWeight() {
    final num? weight = num.tryParse(_packetWeightController.text.trim());
    final int? packets = int.tryParse(_packetsController.text.trim());

    if (weight == null || packets == null) {
      _totalWeightController.text = '';
      return;
    }

    final num total = weight * packets;
    final String next = total == total.roundToDouble()
        ? total.toInt().toString()
        : total.toString();
    if (_totalWeightController.text != next) {
      _totalWeightController.text = next;
    }
  }

  void _onProductSelected(ProductModel product) {
    setState(() {
      _selectedProduct = product;
    });
    _applyAutofill();
  }

  void _applyAutofill() {
    final String? computed = _autofill.nextValue(
      productSellingPrice: _selectedProduct?.sellingPriceValue,
      packetWeight: _packetWeightController.text,
      packets: _packetsController.text,
    );
    if (computed == null || computed == _sellingPriceController.text) return;
    _sellingPriceController.value = TextEditingValue(
      text: computed,
      selection: TextSelection.collapsed(offset: computed.length),
    );
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _packetWeightController.text = _packaging.packetWeight;
    _packetsController.text = _packaging.packetsLabel;
    _sellingPriceController.text = _packaging.sellingPrice;
    _autofill.adoptExistingValue(_sellingPriceController.text);

    _totalWeightController.text = _packaging.totalWeight;

    setState(() {
      _selectedProduct = _resolveSelectedProduct();
      _pickedImage = null;
      _imageRemoved = false;
      _mode = RecordDialogMode.view;
    });
  }

  void _notifyLocked() {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: AppStrings.VIEW_MODE_LOCKED_TOAST_BODY,
    );
  }

  Future<void> _submit() async {
    // Only the selling price is sent, so the (locked) product is not validated.
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    if (!isFormValid) return;

    setState(() => _isSubmitting = true);

    final ProductPackagingsCubit cubit = context.read<ProductPackagingsCubit>();

    final bool succeeded = await cubit.updateProductPackaging(
      publicId: _packaging.publicId,
      sellingPrice: _sellingPriceController.text.trim(),
      image: _pickedImage,
      removeImage: _pickedImage == null && _imageRemoved,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        AppStrings.PRODUCT_PACKAGING_UPDATED_TITLE,
      );
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  List<TextInputFormatter> _decimalFormatters(RegExp pattern) => [
    FilteringTextInputFormatter.allow(_decimalCharacters),
    TextInputFormatter.withFunction(
      (oldValue, newValue) =>
          pattern.hasMatch(newValue.text) ? newValue : oldValue,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.inventory_outlined,
      title: AppStrings.PRODUCT_PACKAGING_DETAIL_TITLE,
      subtitle: AppStrings.PRODUCT_PACKAGING_DETAIL_SUBTITLE,
      mode: _mode,
      body: Form(key: _formKey, child: _buildFields()),
      isTall: true,
      aside: RecordDialogAside(
        title: AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE,
        subtitle: AppStrings.SELECTED_PRODUCT_SUMMARY_HINT,
        child: _buildProductSummary(_selectedProduct),
      ),
      onEdit: _enterEditMode,
      onCancelEdit: _cancelEdit,
      onSubmit: _isSubmitting ? null : _submit,
      isSubmitting: _isSubmitting,
      submitLabel: AppStrings.UPDATE,
    );
  }

  Widget _buildFields() {
    final ProductModel? product = _selectedProduct;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          // The product, like the packet weight and count, is fixed once a
          // packaging exists: only its selling price can be edited.
          left: ProductPickerField(
            value: product,
            products: _products,
            enabled: false,
            isUnavailable: _areProductsUnavailable,
            onBlockedTap: _notifyLocked,
            onSelected: _onProductSelected,
          ),
          right: RecordField(
            controller: _packetWeightController,
            label: AppStrings.FIELD_PACKET_WEIGHT,
            isEditable: false,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _packetsController,
            label: AppStrings.FIELD_PACKETS,
            isEditable: false,
            isLocked: true,
          ),
          right: RecordField(
            controller: _sellingPriceController,
            label: AppStrings.FIELD_BAG_SELLING_PRICE,
            hint: AppStrings.FIELD_BAG_SELLING_PRICE_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            isEditable: _canEdit,
            inputFormatters: _decimalFormatters(_pricePattern),
            onChanged: _autofill.registerFieldChange,
            validator: FormValidators.nonNegativeAmount,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _totalWeightController,
            label: AppStrings.COLUMN_TOTAL_WEIGHT,
            isEditable: _canEdit,
            isLocked: true,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        _buildImageSection(),
      ],
    );
  }

  Future<void> _pickImage() async {
    final FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;

    final PlatformFile file = result.files.first;
    final List<int>? bytes = file.bytes;
    if (bytes == null) return;

    setState(() {
      _pickedImage = ProductPackagingImageUpload(
        bytes: bytes,
        filename: file.name,
      );
      _imageRemoved = false;
    });
  }

  Future<void> _confirmRemoveImage() async {
    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.PACKAGING_REMOVE_IMAGE_TITLE,
      message: AppStrings.PACKAGING_REMOVE_IMAGE_BODY,
      confirmLabel: AppStrings.PACKAGING_REMOVE_IMAGE,
      isDangerous: true,
    );
    if (!confirmed || !mounted) return;

    setState(() {
      _pickedImage = null;
      _imageRemoved = true;
    });
  }

  Widget _buildImageSection() {
    final String existing = _packaging.imageDisplayUrl;
    final String fallback = _packaging.resolvedDisplayImageUrl;
    final bool hasPicked = _pickedImage != null;
    final bool showsOwnImage = hasPicked || (existing.isNotEmpty && !_imageRemoved);

    final Widget preview = Container(
      height: AppSizes.productImagePreview,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      clipBehavior: Clip.antiAlias,
      child: hasPicked
          ? Image.memory(
              Uint8List.fromList(_pickedImage!.bytes),
              fit: BoxFit.contain,
            )
          : (showsOwnImage
                ? Image.network(
                    existing,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stack) =>
                        _buildImagePlaceholder(),
                  )
                : (fallback.isNotEmpty
                      ? Image.network(
                          fallback,
                          fit: BoxFit.contain,
                          errorBuilder: (context, error, stack) =>
                              _buildImagePlaceholder(),
                        )
                      : _buildImagePlaceholder())),
    );

    final String hint = _canEdit
        ? AppStrings.PACKAGING_IMAGE_OPTIONAL
        : (showsOwnImage
              ? AppStrings.IMAGE_VIEW_HINT
              : (fallback.isNotEmpty
                    ? AppStrings.PACKAGING_IMAGE_USING_PRODUCT
                    : AppStrings.PACKAGING_IMAGE_EMPTY));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.PACKAGING_IMAGE_LABEL,
          style: AppTypography.labelStrong,
        ),
        const SizedBox(height: AppSpacing.sm),
        if (!_canEdit && showsOwnImage)
          MouseRegion(
            cursor: SystemMouseCursors.zoomIn,
            child: GestureDetector(
              onTap: () => ImageViewerDialog.show(
                context,
                url: existing,
                title: _packaging.productName,
              ),
              child: preview,
            ),
          )
        else
          preview,
        const SizedBox(height: AppSpacing.sm),
        Text(
          hint,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        if (_canEdit) ...[
          const SizedBox(height: AppSpacing.md),
          Row(
            children: [
              Expanded(
                child: SecondaryButton(
                  label: hasPicked || (existing.isNotEmpty && !_imageRemoved)
                      ? AppStrings.PACKAGING_REPLACE_IMAGE
                      : AppStrings.PACKAGING_PICK_IMAGE,
                  icon: Icons.image_outlined,
                  onPressed: _isSubmitting ? null : _pickImage,
                ),
              ),
              if (showsOwnImage) ...[
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: SecondaryButton(
                    label: AppStrings.PACKAGING_REMOVE_IMAGE,
                    icon: Icons.close_rounded,
                    onPressed: _isSubmitting
                        ? null
                        : (hasPicked
                              ? () => setState(() => _pickedImage = null)
                              : _confirmRemoveImage),
                  ),
                ),
              ],
              if (!showsOwnImage && _imageRemoved && !hasPicked) ...[
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: SecondaryButton(
                    label: AppStrings.PACKAGING_UNDO_REMOVE_IMAGE,
                    icon: Icons.undo_rounded,
                    onPressed: _isSubmitting
                        ? null
                        : () => setState(() => _imageRemoved = false),
                  ),
                ),
              ],
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildImagePlaceholder() {
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
          AppStrings.PACKAGING_IMAGE_EMPTY,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
        ),
      ],
    );
  }

  Widget _buildProductSummary(ProductModel? product) {
    if (product == null) {
      return Text(
        AppStrings.SELECTED_PRODUCT_NONE,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        DetailField(label: AppStrings.COLUMN_NAME, value: product.name),
        const SizedBox(height: AppSpacing.md),
        DetailField(label: AppStrings.COLUMN_CROP, value: product.cropName),
        const SizedBox(height: AppSpacing.md),
        DetailField(label: AppStrings.COLUMN_STAGE, value: product.stageName),
        const SizedBox(height: AppSpacing.md),
        DetailField(
          label: AppStrings.COLUMN_BAG_SELLING_PRICE,
          value: product.sellingPrice,
        ),
      ],
    );
  }
}
