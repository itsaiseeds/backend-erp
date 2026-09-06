import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/crop_model.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/services/crops_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/crop_picker_field.dart';
import '../../data/models/product_model.dart';
import '../bloc/products_cubit.dart';

class ProductFormDialog extends StatefulWidget {
  final ProductModel? product;

  const ProductFormDialog({super.key, this.product});

  static Future<void> show(
    BuildContext context, {
    required ProductsCubit cubit,
    ProductModel? product,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<ProductsCubit>.value(
        value: cubit,
        child: ProductFormDialog(product: product),
      ),
    );
  }

  @override
  State<ProductFormDialog> createState() => _ProductFormDialogState();
}

class _ProductFormDialogState extends State<ProductFormDialog> {
  static final RegExp _decimalPattern = RegExp(r'^\d*\.?\d{0,2}$');
  static final RegExp _decimalCharacters = RegExp(r'[0-9.]');

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  late final TextEditingController _nameController;
  late final TextEditingController _buyingPriceController;
  late final TextEditingController _sellingPriceController;

  List<CropModel> _crops = const [];
  CropModel? _selectedCrop;
  bool _isSubmitting = false;
  bool _isCreatingCrop = false;
  bool _areCropsUnavailable = false;
  String? _cropError;

  bool get _isEditing => widget.product != null;

  bool get _isBusy => _isSubmitting || _isCreatingCrop;

  @override
  void initState() {
    super.initState();
    final ProductModel? product = widget.product;
    _nameController = TextEditingController(text: product?.name ?? '');
    _buyingPriceController = TextEditingController(
      text: product?.buyingPrice ?? '',
    );
    _sellingPriceController = TextEditingController(
      text: product?.sellingPrice ?? '',
    );
    _crops = CropsService.instance.crops;
    _selectedCrop = product?.crop;
    _loadCrops();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _buyingPriceController.dispose();
    _sellingPriceController.dispose();
    super.dispose();
  }

  Future<void> _loadCrops() async {
    final bool succeeded = await CropsService.instance.loadCrops();
    if (!mounted) return;
    setState(() {
      _crops = CropsService.instance.crops;
      _areCropsUnavailable = !succeeded;
    });
  }

  Future<void> _onCreateCropRequested(String name) async {
    final String trimmed = name.trim();
    if (trimmed.isEmpty) return;

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.CROP_CREATE_CONFIRM_TITLE,
      message: CropPickerField.createConfirmationMessage(trimmed),
      confirmLabel: AppStrings.CREATE,
    );
    if (!confirmed || !mounted) return;

    setState(() => _isCreatingCrop = true);

    try {
      final CropModel created = await CropsService.instance.createCrop(trimmed);
      if (!mounted) return;
      setState(() {
        _crops = CropsService.instance.crops;
        _areCropsUnavailable = false;
        _selectedCrop = created;
        _cropError = null;
        _isCreatingCrop = false;
      });
      ToastUtils.showSuccess(context, AppStrings.CROP_CREATED_TITLE);
    } catch (error) {
      if (!mounted) return;
      setState(() => _isCreatingCrop = false);
      ToastUtils.showError(
        context,
        AppStrings.CROP_CREATE_FAILED_TITLE,
        description: error is ApiException
            ? error.message
            : AppStrings.SOMETHING_WENT_WRONG,
      );
    }
  }

  Future<void> _submit() async {
    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCropValid = _selectedCrop != null;

    setState(
      () =>
          _cropError = isCropValid ? null : AppStrings.VALIDATION_CROP_REQUIRED,
    );

    if (!isFormValid || !isCropValid) return;

    setState(() => _isSubmitting = true);

    final ProductsCubit cubit = context.read<ProductsCubit>();

    final bool succeeded = _isEditing
        ? await cubit.updateProduct(
            publicId: widget.product!.publicId,
            name: _nameController.text.trim(),
            cropId: _selectedCrop!.id,
            buyingPrice: _buyingPriceController.text.trim(),
            sellingPrice: _sellingPriceController.text.trim(),
          )
        : await cubit.createProduct(
            name: _nameController.text.trim(),
            cropId: _selectedCrop!.id,
            buyingPrice: _buyingPriceController.text.trim(),
            sellingPrice: _sellingPriceController.text.trim(),
          );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        _isEditing
            ? AppStrings.PRODUCT_UPDATED_TITLE
            : AppStrings.PRODUCT_CREATED_TITLE,
      );
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  List<TextInputFormatter> get _priceFormatters => [
    FilteringTextInputFormatter.allow(_decimalCharacters),
    TextInputFormatter.withFunction(
      (oldValue, newValue) =>
          _decimalPattern.hasMatch(newValue.text) ? newValue : oldValue,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.inventory_2_outlined,
      title: _isEditing ? AppStrings.EDIT_PRODUCT : AppStrings.ADD_PRODUCT,
      subtitle: _isEditing
          ? AppStrings.EDIT_PRODUCT_SUBTITLE
          : AppStrings.ADD_PRODUCT_SUBTITLE,
      submitLabel: _isEditing ? AppStrings.UPDATE : AppStrings.CREATE,
      isSubmitting: _isBusy,
      onSubmit: _isBusy ? null : _submit,
      content: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            AppTextField(
              controller: _nameController,
              label: AppStrings.FIELD_PRODUCT_NAME,
              hint: AppStrings.FIELD_PRODUCT_NAME_HINT,
              enabled: !_isBusy,
              validator: FormValidators.requiredField,
            ),
            const SizedBox(height: AppSpacing.md),
            CropPickerField(
              value: _selectedCrop,
              crops: _crops,
              enabled: !_isBusy,
              errorText: _cropError,
              isUnavailable: _areCropsUnavailable,
              onSelected: (crop) => setState(() {
                _selectedCrop = crop;
                _cropError = null;
              }),
              onCreateRequested: _onCreateCropRequested,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _buyingPriceController,
              label: AppStrings.FIELD_BUYING_PRICE,
              hint: AppStrings.FIELD_BUYING_PRICE_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isBusy,
              inputFormatters: _priceFormatters,
              validator: FormValidators.nonNegativeAmount,
            ),
            const SizedBox(height: AppSpacing.md),
            AppTextField(
              controller: _sellingPriceController,
              label: AppStrings.FIELD_SELLING_PRICE,
              hint: AppStrings.FIELD_SELLING_PRICE_HINT,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              enabled: !_isBusy,
              inputFormatters: _priceFormatters,
              validator: FormValidators.nonNegativeAmount,
            ),
          ],
        ),
      ),
    );
  }
}
