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
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
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
  static final RegExp _weightPattern = RegExp(r'^\d*\.?\d{0,3}$');
  static final RegExp _pricePattern = RegExp(r'^\d*\.?\d{0,2}$');
  static final RegExp _decimalCharacters = RegExp(r'[0-9.]');
  static final RegExp _digitCharacters = RegExp(r'[0-9]');

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final SellingPriceAutofill _autofill = SellingPriceAutofill();

  late final TextEditingController _packetWeightController;
  late final TextEditingController _packetsController;
  late final TextEditingController _sellingPriceController;
  late final TextEditingController _totalWeightController;

  late RecordDialogMode _mode;

  List<ProductModel> _products = const [];
  ProductModel? _selectedProduct;
  bool _isSubmitting = false;
  bool _areProductsUnavailable = false;
  String? _productError;

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
      _productError = null;
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
      _productError = null;
      _mode = RecordDialogMode.view;
    });
  }

  void _notifyViewMode() {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: AppStrings.VIEW_MODE_TOAST_BODY,
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

    final bool succeeded = await cubit.updateProductPackaging(
      publicId: _packaging.publicId,
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

  List<TextInputFormatter> get _countFormatters => [
    FilteringTextInputFormatter.allow(_digitCharacters),
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
          left: ProductPickerField(
            value: product,
            products: _products,
            enabled: _canEdit,
            errorText: _productError,
            isUnavailable: _areProductsUnavailable,
            onBlockedTap: _notifyViewMode,
            onSelected: _onProductSelected,
          ),
          right: RecordField(
            controller: _packetWeightController,
            label: AppStrings.FIELD_PACKET_WEIGHT,
            hint: AppStrings.FIELD_PACKET_WEIGHT_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            isEditable: _canEdit,
            inputFormatters: _decimalFormatters(_weightPattern),
            validator: FormValidators.positiveAmount,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _packetsController,
            label: AppStrings.FIELD_PACKETS,
            hint: AppStrings.FIELD_PACKETS_HINT,
            keyboardType: TextInputType.number,
            isEditable: _canEdit,
            inputFormatters: _countFormatters,
            validator: FormValidators.positiveCount,
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
