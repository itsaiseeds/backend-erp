import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/widgets/feedback/form_step_indicator.dart';
import '../../../../core/models/stage_model.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/inputs/searchable_popup_menu.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
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
  late final TextEditingController _sellingPriceController;
  late final List<TextEditingController> _descriptionControllers;

  List<CropModel> _crops = const [];
  CropModel? _selectedCrop;
  StageModel? _selectedStage;
  String? _stageError;
  int _step = 0;
  ProductImageUpload? _pickedImage;
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
    _sellingPriceController = TextEditingController(
      text: product?.sellingPrice ?? '',
    );

    final List<String> items = product?.descriptionItems ?? const [];
    _descriptionControllers = items.isEmpty
        ? [TextEditingController()]
        : items.map((item) => TextEditingController(text: item)).toList();

    _crops = CropsService.instance.crops;
    _selectedCrop = product?.crop;
    _selectedStage = product?.stage;
    _loadCrops();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _sellingPriceController.dispose();
    for (final controller in _descriptionControllers) {
      controller.dispose();
    }
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
    final bool isCropValid = _selectedCrop != null;
    final bool isStageValid = _selectedStage != null;

    setState(() {
      _cropError = isCropValid ? null : AppStrings.VALIDATION_CROP_REQUIRED;
      _stageError = isStageValid
          ? null
          : AppStrings.VALIDATION_STAGE_REQUIRED;
    });

    if (!isCropValid) {
      setState(() => _step = 0);
      return;
    }
    if (!isStageValid) {
      setState(() => _step = 1);
      return;
    }

    setState(() => _isSubmitting = true);

    final ProductsCubit cubit = context.read<ProductsCubit>();

    final bool succeeded = _isEditing
        ? await cubit.updateProduct(
            publicId: widget.product!.publicId,
            name: _nameController.text.trim(),
            cropId: _selectedCrop!.id,
            stageId: _selectedStage!.id,
            sellingPrice: _sellingPriceController.text.trim(),
            image: _pickedImage,
            descriptionItems: _descriptionItems,
          )
        : await cubit.createProduct(
            name: _nameController.text.trim(),
            cropId: _selectedCrop!.id,
            stageId: _selectedStage!.id,
            sellingPrice: _sellingPriceController.text.trim(),
            image: _pickedImage,
            descriptionItems: _descriptionItems,
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

  List<String> get _descriptionItems => _descriptionControllers
      .map((controller) => controller.text.trim())
      .where((item) => item.isNotEmpty)
      .toList();

  void _addDescriptionPoint() {
    setState(() => _descriptionControllers.add(TextEditingController()));
  }

  void _removeDescriptionPoint(int index) {
    setState(() {
      _descriptionControllers.removeAt(index).dispose();
      if (_descriptionControllers.isEmpty) {
        _descriptionControllers.add(TextEditingController());
      }
    });
  }

  Widget _buildStagePicker() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(AppStrings.COLUMN_STAGE, style: AppTypography.labelStrong),
        const SizedBox(height: AppSpacing.sm),
        SearchablePopupMenu<StageModel>(
          items: Stages.all,
          itemToString: (stage) => stage.label,
          isSelected: (stage) => stage.id == _selectedStage?.id,
          onSelected: (stage) => setState(() {
            _selectedStage = stage;
            _stageError = null;
          }),
          child: Container(
            height: AppSizes.inputHeight,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
            decoration: BoxDecoration(
              color: _isBusy ? AppColors.SURFACE_VARIANT : AppColors.SURFACE,
              border: Border.all(
                color: _stageError != null
                    ? AppColors.ERROR
                    : AppColors.BORDER,
              ),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    _selectedStage?.label ?? AppStrings.PRODUCT_STAGE_HINT,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      color: _selectedStage == null
                          ? AppColors.TEXT_DISABLED
                          : AppColors.TEXT_PRIMARY,
                    ),
                  ),
                ),
                const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: AppSizes.iconLg,
                  color: AppColors.TEXT_SECONDARY,
                ),
              ],
            ),
          ),
        ),
        if (_stageError != null) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            _stageError!,
            style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
          ),
        ],
      ],
    );
  }

  Widget _buildDescriptionItems() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.PRODUCT_DESCRIPTION_LABEL,
          style: AppTypography.labelStrong,
        ),
        const SizedBox(height: AppSpacing.sm),
        for (int index = 0; index < _descriptionControllers.length; index++)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Expanded(
                  child: AppTextField(
                    controller: _descriptionControllers[index],
                    hint: AppStrings.PRODUCT_POINT_HINT,
                    enabled: !_isBusy,
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                IconActionButton(
                  icon: Icons.delete_outline_rounded,
                  tooltip: AppStrings.PRODUCT_REMOVE_POINT,
                  type: IconActionType.error,
                  onPressed: _isBusy || _descriptionControllers.length == 1
                      ? null
                      : () => _removeDescriptionPoint(index),
                ),
              ],
            ),
          ),
        SecondaryButton(
          label: AppStrings.PRODUCT_ADD_POINT,
          icon: Icons.add_rounded,
          onPressed: _isBusy ? null : _addDescriptionPoint,
        ),
      ],
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
    final bool isLastStep = _step == 2;

    return AppFormDialog(
      icon: Icons.inventory_2_outlined,
      title: _isEditing ? AppStrings.EDIT_PRODUCT : AppStrings.ADD_PRODUCT,
      subtitle: _isEditing
          ? AppStrings.EDIT_PRODUCT_SUBTITLE
          : AppStrings.ADD_PRODUCT_SUBTITLE,
      submitLabel: isLastStep
          ? (_isEditing ? AppStrings.UPDATE : AppStrings.CREATE)
          : AppStrings.STEP_NEXT,
      isSubmitting: _isBusy,
      fixedHeight: AppSizes.formDialogFixedHeight,
      onSubmit: _isBusy ? null : (isLastStep ? _submit : _next),
      leadingAction: _step == 0
          ? null
          : SecondaryButton(
              label: AppStrings.STEP_BACK,
              onPressed: _isBusy ? null : _back,
            ),
      content: Form(
        key: _formKey,
        child: Column(
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
              onStepTapped: _isBusy ? null : _goTo,
            ),
            const SizedBox(height: AppSpacing.lg),
            _buildStepBody(),
          ],
        ),
      ),
    );
  }

  void _goTo(int step) {
    if (step > _step && !_validateStep(_step)) return;
    setState(() => _step = step);
  }

  void _next() {
    if (!_validateStep(_step)) return;
    setState(() => _step += 1);
  }

  void _back() => setState(() => _step -= 1);

  bool _validateStep(int step) {
    if (step != 0) return true;

    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCropValid = _selectedCrop != null;

    setState(
      () =>
          _cropError = isCropValid ? null : AppStrings.VALIDATION_CROP_REQUIRED,
    );

    return isFormValid && isCropValid;
  }

  Widget _buildStepBody() {
    switch (_step) {
      case 0:
        return _buildBasicsStep();
      case 1:
        return _buildDetailsStep();
      default:
        return _buildImageStep();
    }
  }

  Widget _buildBasicsStep() {
    return Column(
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
          controller: _sellingPriceController,
          label: AppStrings.FIELD_SELLING_PRICE,
          hint: AppStrings.FIELD_SELLING_PRICE_HINT,
          helperText: AppStrings.FIELD_SELLING_PRICE_HELPER,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          enabled: !_isBusy,
          inputFormatters: _priceFormatters,
          validator: FormValidators.nonNegativeAmount,
        ),
      ],
    );
  }

  Widget _buildDetailsStep() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildStagePicker(),
        const SizedBox(height: AppSpacing.md),
        _buildDescriptionItems(),
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

    setState(
      () => _pickedImage = ProductImageUpload(
        bytes: bytes,
        filename: file.name,
      ),
    );
  }

  Widget _buildImageStep() {
    final String existing = widget.product?.imageDisplayUrl ?? '';
    final bool hasPicked = _pickedImage != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
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
              : (existing.isNotEmpty
                    ? Image.network(
                        existing,
                        fit: BoxFit.contain,
                        errorBuilder: (context, error, stack) =>
                            _buildImagePlaceholder(),
                      )
                    : _buildImagePlaceholder()),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          AppStrings.PRODUCT_IMAGE_OPTIONAL,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        SecondaryButton(
          label: hasPicked || existing.isNotEmpty
              ? AppStrings.PRODUCT_REPLACE_IMAGE
              : AppStrings.PRODUCT_PICK_IMAGE,
          icon: Icons.image_outlined,
          onPressed: _isBusy ? null : _pickImage,
        ),
        if (hasPicked) ...[
          const SizedBox(height: AppSpacing.sm),
          SecondaryButton(
            label: AppStrings.PRODUCT_REMOVE_IMAGE,
            icon: Icons.close_rounded,
            onPressed: _isBusy ? null : () => setState(() => _pickedImage = null),
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
          AppStrings.PRODUCT_IMAGE_EMPTY,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
        ),
      ],
    );
  }

}
