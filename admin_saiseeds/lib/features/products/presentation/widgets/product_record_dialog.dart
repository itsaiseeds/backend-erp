import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/models/crop_model.dart';
import '../../../../core/models/stage_model.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/services/crops_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../../core/widgets/feedback/image_viewer_dialog.dart';
import '../../../../core/widgets/inputs/crop_picker_field.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/product_model.dart';
import '../bloc/products_cubit.dart';

class ProductRecordDialog extends StatefulWidget {
  final ProductModel product;
  final RecordDialogMode initialMode;

  const ProductRecordDialog({
    super.key,
    required this.product,
    this.initialMode = RecordDialogMode.view,
  });

  static Future<void> show(
    BuildContext context,
    ProductModel product, {
    required ProductsCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<ProductsCubit>.value(
        value: cubit,
        child: ProductRecordDialog(
          product: product,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<ProductRecordDialog> createState() => _ProductRecordDialogState();
}

class _ProductRecordDialogState extends State<ProductRecordDialog> {
  static final RegExp _decimalPattern = RegExp(r'^\d*\.?\d{0,2}$');
  static final RegExp _decimalCharacters = RegExp(r'[0-9.]');

  static const List<String> _stepLabels = [
    AppStrings.PRODUCT_STEP_BASIC,
    AppStrings.PRODUCT_STEP_DETAILS,
    AppStrings.PRODUCT_STEP_IMAGE,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  late final TextEditingController _nameController;
  late final TextEditingController _sellingPriceController;
  late List<TextEditingController> _descriptionControllers;

  late RecordDialogMode _mode;
  int _step = 0;

  List<CropModel> _crops = const [];
  CropModel? _selectedCrop;
  StageModel? _selectedStage;
  ProductImageUpload? _pickedImage;

  bool _isSubmitting = false;
  bool _isCreatingCrop = false;
  bool _areCropsUnavailable = false;
  String? _cropError;
  String? _stageError;

  ProductModel get _product => widget.product;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _isBusy => _isSubmitting || _isCreatingCrop;

  bool get _canEdit => _isEditing && !_isBusy;

  bool get _isFirstStep => _step == 0;

  bool get _isLastStep => _step == _stepLabels.length - 1;

  String get _stepCaption =>
      '${AppStrings.CLIENT_STEP_PROGRESS} ${_step + 1}/${_stepLabels.length}'
      ' · ${_stepLabels[_step]}';

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _nameController = TextEditingController(text: _product.name);
    _sellingPriceController = TextEditingController(
      text: _product.sellingPrice,
    );
    _descriptionControllers = _controllersFor(_product.descriptionItems);

    _crops = CropsService.instance.crops;
    _selectedCrop = _product.crop;
    _selectedStage = _product.stage;
    _loadCrops();
  }

  List<TextEditingController> _controllersFor(List<String> items) {
    if (items.isEmpty) return [TextEditingController()];
    return items.map((item) => TextEditingController(text: item)).toList();
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

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    _nameController.text = _product.name;
    _sellingPriceController.text = _product.sellingPrice;
    for (final controller in _descriptionControllers) {
      controller.dispose();
    }

    setState(() {
      _descriptionControllers = _controllersFor(_product.descriptionItems);
      _selectedCrop = _product.crop;
      _selectedStage = _product.stage;
      _pickedImage = null;
      _cropError = null;
      _stageError = null;
      _mode = RecordDialogMode.view;
    });
  }

  void _next() {
    if (_isEditing && !_validateStep(_step)) return;
    setState(() => _step += 1);
  }

  void _back() => setState(() => _step -= 1);

  bool _validateStep(int step) {
    if (step != 0) return true;

    final bool isFormValid = _formKey.currentState?.validate() ?? false;
    final bool isCropValid = _selectedCrop != null;
    final bool isStageValid = _selectedStage != null;

    setState(() {
      _cropError = isCropValid ? null : AppStrings.VALIDATION_CROP_REQUIRED;
      _stageError = isStageValid ? null : AppStrings.VALIDATION_STAGE_REQUIRED;
    });

    return isFormValid && isCropValid && isStageValid;
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
      _stageError = isStageValid ? null : AppStrings.VALIDATION_STAGE_REQUIRED;
    });

    if (!isCropValid) {
      setState(() => _step = 0);
      return;
    }
    if (!isStageValid) {
      setState(() => _step = 0);
      return;
    }

    setState(() => _isSubmitting = true);

    final ProductsCubit cubit = context.read<ProductsCubit>();

    final bool succeeded = await cubit.updateProduct(
      publicId: _product.publicId,
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
      ToastUtils.showSuccess(context, AppStrings.PRODUCT_UPDATED_TITLE);
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

  List<TextInputFormatter> get _priceFormatters => [
    FilteringTextInputFormatter.allow(_decimalCharacters),
    TextInputFormatter.withFunction(
      (oldValue, newValue) =>
          _decimalPattern.hasMatch(newValue.text) ? newValue : oldValue,
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.inventory_2_outlined,
      title: AppStrings.PRODUCT_DETAIL_TITLE,
      subtitle: '${_product.name} · $_stepCaption',
      mode: _mode,
      body: Form(key: _formKey, child: _buildStepBody()),
      isBodyFlush: true,
      onEdit: _enterEditMode,
      showFooterInViewMode: true,
      onCancelEdit: _isFirstStep ? _cancelEdit : _back,
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      isCancelEnabled: _isEditing || !_isFirstStep,
      onSubmit: _isBusy
          ? null
          : (_isLastStep ? (_isEditing ? _submit : null) : _next),
      submitLabel: _isLastStep ? AppStrings.UPDATE : AppStrings.STEP_NEXT,
      isSubmitting: _isSubmitting,
    );
  }

  Widget _buildStepBody() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: switch (_step) {
        0 => _buildBasics(),
        1 => _buildDetails(),
        _ => _buildImage(),
      },
    );
  }

  Widget _buildBasics() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: RecordField(
            controller: _nameController,
            label: AppStrings.FIELD_PRODUCT_NAME,
            hint: AppStrings.FIELD_PRODUCT_NAME_HINT,
            isEditable: _canEdit,
            validator: FormValidators.requiredField,
          ),
          right: CropPickerField(
            value: _selectedCrop,
            crops: _crops,
            enabled: _canEdit,
            errorText: _cropError,
            isUnavailable: _areCropsUnavailable,
            onBlockedTap: _notifyViewMode,
            onSelected: (crop) => setState(() {
              _selectedCrop = crop;
              _cropError = null;
            }),
            onCreateRequested: _onCreateCropRequested,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: RecordField(
            controller: _sellingPriceController,
            label: AppStrings.FIELD_SELLING_PRICE,
            hint: AppStrings.FIELD_SELLING_PRICE_HINT,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            isEditable: _canEdit,
            inputFormatters: _priceFormatters,
            validator: FormValidators.nonNegativeAmount,
          ),
          right: SearchableField<StageModel>(
            label: AppStrings.COLUMN_STAGE,
            hintText: AppStrings.PRODUCT_STAGE_HINT,
            value: _selectedStage,
            items: Stages.all,
            itemToString: (stage) => stage.label,
            isSame: (a, b) => a.id == b.id,
            enabled: _canEdit,
            errorText: _stageError,
            onBlockedTap: _notifyViewMode,
            onSelected: (stage) => setState(() {
              _selectedStage = stage;
              _stageError = null;
            }),
          ),
        ),
      ],
    );
  }

  void _notifyViewMode() {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: AppStrings.VIEW_MODE_TOAST_BODY,
    );
  }

  Widget _buildDetails() => _buildDescriptionItems();

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
                  child: RecordField(
                    controller: _descriptionControllers[index],
                    hint: AppStrings.PRODUCT_POINT_HINT,
                    isEditable: _canEdit,
                  ),
                ),
                if (_canEdit) ...[
                  const SizedBox(width: AppSpacing.sm),
                  IconActionButton(
                    icon: Icons.delete_outline_rounded,
                    tooltip: AppStrings.PRODUCT_REMOVE_POINT,
                    type: IconActionType.error,
                    onPressed: _descriptionControllers.length == 1
                        ? null
                        : () => _removeDescriptionPoint(index),
                  ),
                ],
              ],
            ),
          ),
        if (_canEdit)
          SecondaryButton(
            label: AppStrings.PRODUCT_ADD_POINT,
            icon: Icons.add_rounded,
            onPressed: _addDescriptionPoint,
          ),
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
      () =>
          _pickedImage = ProductImageUpload(bytes: bytes, filename: file.name),
    );
  }

  Widget _buildImage() {
    final String existing = _product.imageDisplayUrl;
    final bool hasPicked = _pickedImage != null;

    final Widget preview = _imageFrame(
      child: hasPicked
          ? Image.memory(
              Uint8List.fromList(_pickedImage!.bytes),
              fit: BoxFit.contain,
            )
          : (existing.isNotEmpty
                ? Image.network(
                    existing,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stack) => _buildPlaceholder(),
                  )
                : _buildPlaceholder()),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (!_canEdit && existing.isNotEmpty)
          MouseRegion(
            cursor: SystemMouseCursors.zoomIn,
            child: GestureDetector(
              onTap: () => ImageViewerDialog.show(
                context,
                url: existing,
                title: _product.name,
              ),
              child: preview,
            ),
          )
        else
          preview,
        const SizedBox(height: AppSpacing.sm),
        Text(
          _canEdit
              ? AppStrings.PRODUCT_IMAGE_OPTIONAL
              : AppStrings.IMAGE_VIEW_HINT,
          textAlign: _canEdit ? TextAlign.start : TextAlign.center,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        if (_canEdit) ...[
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
              onPressed: _isBusy
                  ? null
                  : () => setState(() => _pickedImage = null),
            ),
          ],
        ],
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
