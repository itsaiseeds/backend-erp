import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/product_picker_field.dart';
import '../../../../core/widgets/layout/app_surface_card.dart';
import '../../../products/data/models/product_model.dart';
import '../../data/models/product_packaging_model.dart';
import '../bloc/product_packagings_cubit.dart';
import 'selling_price_autofill.dart';

class ProductPackagingFormDialog extends StatefulWidget {
  final ProductPackagingModel? packaging;

  const ProductPackagingFormDialog({super.key, this.packaging});

  static Future<void> show(
    BuildContext context, {
    required ProductPackagingsCubit cubit,
    ProductPackagingModel? packaging,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<ProductPackagingsCubit>.value(
        value: cubit,
        child: ProductPackagingFormDialog(packaging: packaging),
      ),
    );
  }

  @override
  State<ProductPackagingFormDialog> createState() =>
      _ProductPackagingFormDialogState();
}

class _ProductPackagingFormDialogState
    extends State<ProductPackagingFormDialog> {
  static final RegExp _weightPattern = RegExp(r'^\d*\.?\d{0,3}$');
  static final RegExp _pricePattern = RegExp(r'^\d*\.?\d{0,2}$');
  static final RegExp _decimalCharacters = RegExp(r'[0-9.]');
  static final RegExp _digitCharacters = RegExp(r'[0-9]');

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final SellingPriceAutofill _autofill = SellingPriceAutofill();
  late final TextEditingController _packetWeightController;
  late final TextEditingController _packetsController;
  late final TextEditingController _sellingPriceController;

  List<ProductModel> _products = const [];
  ProductModel? _selectedProduct;
  bool _isSubmitting = false;
  bool _areProductsUnavailable = false;
  String? _productError;

  bool get _isEditing => widget.packaging != null;

  @override
  void initState() {
    super.initState();
    final ProductPackagingModel? packaging = widget.packaging;
    _packetWeightController = TextEditingController(
      text: packaging?.packetWeight ?? '',
    );
    _packetsController = TextEditingController(
      text: packaging?.packetsLabel ?? '',
    );
    _sellingPriceController = TextEditingController(
      text: packaging?.sellingPrice ?? '',
    );
    _autofill.adoptExistingValue(_sellingPriceController.text);
    _products = ProductsService.instance.products;
    _selectedProduct = _resolveSelectedProduct();
    _packetsController.addListener(_onPacketsChanged);
    _loadProducts();
  }

  @override
  void dispose() {
    _packetsController.removeListener(_onPacketsChanged);
    _packetWeightController.dispose();
    _packetsController.dispose();
    _sellingPriceController.dispose();
    super.dispose();
  }

  ProductModel? _resolveSelectedProduct() {
    final String publicId = widget.packaging?.productPublicId ?? '';
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

  void _onPacketsChanged() => _applyAutofill();

  void _onProductSelected(ProductModel product) {
    setState(() {
      _selectedProduct = product;
      _productError = null;
    });
    _applyAutofill();
  }

  void _applyAutofill() {
    final String? computed = _autofill.nextValue(
      productSellingPrice: _selectedProduct?.sellingPriceValue,
      packets: _packetsController.text,
    );
    if (computed == null || computed == _sellingPriceController.text) return;
    _sellingPriceController.value = TextEditingValue(
      text: computed,
      selection: TextSelection.collapsed(offset: computed.length),
    );
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isProductValid = _selectedProduct != null;

    setState(
      () => _productError = isProductValid
          ? null
          : AppStrings.VALIDATION_PRODUCT_REQUIRED,
    );

    if (!isFormValid || !isProductValid) return;

    setState(() => _isSubmitting = true);

    final ProductPackagingsCubit cubit = context.read<ProductPackagingsCubit>();

    final bool succeeded = _isEditing
        ? await cubit.updateProductPackaging(
            publicId: widget.packaging!.publicId,
            productPublicId: _selectedProduct!.publicId,
            packetWeight: _packetWeightController.text.trim(),
            packets: _packetsController.text.trim(),
            sellingPrice: _sellingPriceController.text.trim(),
          )
        : await cubit.createProductPackaging(
            productPublicId: _selectedProduct!.publicId,
            packetWeight: _packetWeightController.text.trim(),
            packets: _packetsController.text.trim(),
            sellingPrice: _sellingPriceController.text.trim(),
          );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        _isEditing
            ? AppStrings.PRODUCT_PACKAGING_UPDATED_TITLE
            : AppStrings.PRODUCT_PACKAGING_CREATED_TITLE,
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

  List<TextInputFormatter> get _countFormatters => [
    FilteringTextInputFormatter.allow(_digitCharacters),
  ];

  Widget _buildProductSummary(ProductModel product) {
    return AppSurfaceCard(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.SELECTED_PRODUCT_SUMMARY_TITLE,
            style: AppTypography.labelStrong,
          ),
          const SizedBox(height: AppSpacing.smd),
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
            ],
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final ProductModel? product = _selectedProduct;

    return AppFormDialog(
      icon: Icons.inventory_outlined,
      title: _isEditing
          ? AppStrings.EDIT_PRODUCT_PACKAGING
          : AppStrings.ADD_PRODUCT_PACKAGING,
      subtitle: _isEditing
          ? AppStrings.EDIT_PRODUCT_PACKAGING_SUBTITLE
          : AppStrings.ADD_PRODUCT_PACKAGING_SUBTITLE,
      submitLabel: _isEditing ? AppStrings.UPDATE : AppStrings.CREATE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            ProductPickerField(
              value: product,
              products: _products,
              enabled: !_isSubmitting,
              errorText: _productError,
              isUnavailable: _areProductsUnavailable,
              onSelected: _onProductSelected,
            ),
            if (product != null) ...[
              const SizedBox(height: AppSpacing.md),
              _buildProductSummary(product),
            ],
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _packetWeightController,
              label: AppStrings.FIELD_PACKET_WEIGHT,
              hint: AppStrings.FIELD_PACKET_WEIGHT_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: _decimalFormatters(_weightPattern),
              validator: FormValidators.positiveAmount,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _packetsController,
              label: AppStrings.FIELD_PACKETS,
              hint: AppStrings.FIELD_PACKETS_HINT,
              keyboardType: TextInputType.number,
              enabled: !_isSubmitting,
              inputFormatters: _countFormatters,
              validator: FormValidators.positiveCount,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _sellingPriceController,
              label: AppStrings.FIELD_SELLING_PRICE,
              hint: AppStrings.FIELD_SELLING_PRICE_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isSubmitting,
              inputFormatters: _decimalFormatters(_pricePattern),
              onChanged: _autofill.registerFieldChange,
              validator: FormValidators.nonNegativeAmount,
            ),
          ],
        ),
      ),
    );
  }
}
