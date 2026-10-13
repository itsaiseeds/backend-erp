import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../products/data/models/product_model.dart';
import '../../../products/data/products_repository.dart';
import '../../../raw_material_stock/data/models/raw_material_stock_model.dart';
import '../../../raw_material_stock/data/raw_material_stock_repository.dart';
import '../../data/product_stock_transfer_repository.dart';

/// Moves raw-material stock from one product to another of the same crop --
/// two products can share the same underlying seed (e.g. SAI-33 and
/// SAI-Balwan), and this lets the office correct which product that in-use
/// stock is currently sitting under. Kilograms only; the server is the one
/// that actually enforces "same crop", "different products" and "source has
/// enough idle stock" -- this screen's own checks, and the live available-kg
/// figures it shows, are a head start so a bad pick never reaches the
/// request.
class ProductStockTransferView extends StatefulWidget {
  const ProductStockTransferView({super.key});

  @override
  State<ProductStockTransferView> createState() =>
      _ProductStockTransferViewState();
}

class _ProductStockTransferViewState extends State<ProductStockTransferView> {
  final TextEditingController _quantityController = TextEditingController();

  ProductModel? _source;
  ProductModel? _target;
  Map<String, RawMaterialStockLineModel> _stockByProduct = const {};
  bool _isLoading = true;
  bool _isSubmitting = false;

  String? _sourceError;
  String? _targetError;
  String? _quantityError;

  num get _quantityValue => num.tryParse(_quantityController.text.trim()) ?? 0;

  @override
  void initState() {
    super.initState();
    _loadData();
    _quantityController.addListener(_onQuantityChanged);
  }

  @override
  void dispose() {
    _quantityController.removeListener(_onQuantityChanged);
    _quantityController.dispose();
    super.dispose();
  }

  void _onQuantityChanged() => setState(() {});

  Future<void> _loadData() async {
    final ApiClient apiClient = context.read<ApiClient>();
    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );

    final List<dynamic> results = await Future.wait([
      ProductsService.instance.loadProducts(),
      RawMaterialStockRepository(
        apiClient: apiClient,
      ).fetchRawMaterialStock().catchError(
        (_) => const RawMaterialStockModel(),
      ),
    ]);
    if (!mounted) return;

    final RawMaterialStockModel stock = results[1] as RawMaterialStockModel;
    setState(() {
      _stockByProduct = {
        for (final RawMaterialStockLineModel line in stock.lines)
          line.productPublicId: line,
      };
      _isLoading = false;
    });
  }

  List<ProductModel> get _usableProducts => ProductsService.instance.products
      .where((product) => product.isUsable)
      .toList();

  /// Target options limited to the source's own crop -- same intent as the
  /// server's own rule, just applied before the picker ever opens.
  List<ProductModel> get _targetOptions {
    final ProductModel? source = _source;
    if (source == null) return const [];
    return _usableProducts
        .where(
          (product) =>
              product.publicId != source.publicId &&
              product.cropId == source.cropId,
        )
        .toList();
  }

  num? _availableKgOf(ProductModel? product) {
    if (product == null) return null;
    return _stockByProduct[product.publicId]?.availableValue;
  }

  void _selectSource(ProductModel product) {
    setState(() {
      _source = product;
      _sourceError = null;
      // A target from a different crop (or the new source itself) can no
      // longer be valid, so it is cleared rather than silently kept.
      if (_target != null &&
          (_target!.publicId == product.publicId ||
              _target!.cropId != product.cropId)) {
        _target = null;
      }
    });
  }

  bool _validate() {
    final String quantity = _quantityController.text.trim();
    final double? value = double.tryParse(quantity);

    setState(() {
      _sourceError = _source == null
          ? AppStrings.TRANSFER_VALIDATION_SOURCE
          : null;
      _targetError = _target == null
          ? AppStrings.TRANSFER_VALIDATION_TARGET
          : (_source != null && _target!.publicId == _source!.publicId
                ? AppStrings.TRANSFER_VALIDATION_SAME_PRODUCT
                : null);
      _quantityError = quantity.isEmpty || value == null
          ? AppStrings.TRANSFER_VALIDATION_QUANTITY
          : (value <= 0
                ? AppStrings.TRANSFER_VALIDATION_QUANTITY_POSITIVE
                : null);
    });

    return _sourceError == null &&
        _targetError == null &&
        _quantityError == null;
  }

  Future<void> _submit() async {
    if (_isSubmitting || !_validate()) return;
    setState(() => _isSubmitting = true);

    final ProductStockTransferRepository repository =
        ProductStockTransferRepository(apiClient: context.read<ApiClient>());

    try {
      final result = await repository.transfer(
        sourceProductPublicId: _source!.publicId,
        targetProductPublicId: _target!.publicId,
        quantityKg: _quantityController.text.trim(),
      );
      if (!mounted) return;
      ToastUtils.showSuccess(context, AppStrings.TRANSFER_DONE);
      setState(() {
        // The response carries fresh balances for exactly the two products
        // touched -- cheaper and more current than refetching the whole
        // report, and keeps the stat cards honest if the admin transfers
        // again right away.
        _stockByProduct = {
          ..._stockByProduct,
          result.source.publicId: RawMaterialStockLineModel(
            productPublicId: result.source.publicId,
            name: result.source.name,
            availableKg: result.source.availableKg,
          ),
          result.target.publicId: RawMaterialStockLineModel(
            productPublicId: result.target.publicId,
            name: result.target.name,
            availableKg: result.target.availableKg,
          ),
        };
        _source = null;
        _target = null;
        _isSubmitting = false;
      });
      _quantityController.clear();
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _isSubmitting = false);
      ToastUtils.showError(context, error.message);
    } catch (_) {
      if (!mounted) return;
      setState(() => _isSubmitting = false);
      ToastUtils.showError(context, AppStrings.SOMETHING_WENT_WRONG);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(),
          const SizedBox(height: AppSpacing.xl),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.xxl),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else
            LayoutBuilder(
              builder: (context, constraints) {
                final bool isWide = constraints.maxWidth >= 860;
                return Flex(
                  direction: isWide ? Axis.horizontal : Axis.vertical,
                  crossAxisAlignment: isWide
                      ? CrossAxisAlignment.start
                      : CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      flex: isWide ? 3 : 0,
                      child: _TransferCard(
                        source: _source,
                        target: _target,
                        sourceAvailableKg: _availableKgOf(_source),
                        targetAvailableKg: _availableKgOf(_target),
                        quantityKg: _quantityValue,
                        usableProducts: _usableProducts,
                        targetOptions: _targetOptions,
                        quantityController: _quantityController,
                        isSubmitting: _isSubmitting,
                        sourceError: _sourceError,
                        targetError: _targetError,
                        quantityError: _quantityError,
                        onSelectSource: _selectSource,
                        onSelectTarget: (product) => setState(() {
                          _target = product;
                          _targetError = null;
                        }),
                        onQuantityErrorClear: () {
                          if (_quantityError != null) {
                            setState(() => _quantityError = null);
                          }
                        },
                        onSubmit: _submit,
                      ),
                    ),
                    SizedBox(
                      width: isWide ? AppSpacing.xl : 0,
                      height: isWide ? 0 : AppSpacing.xl,
                    ),
                    if (isWide)
                      const Expanded(flex: 2, child: _InfoPanel())
                    else
                      const _InfoPanel(),
                  ],
                );
              },
            ),
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Container(
          width: AppSizes.dialogHeaderIconBox,
          height: AppSizes.dialogHeaderIconBox,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.PRIMARY_SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: const Icon(
            Icons.swap_horiz_rounded,
            size: AppSizes.iconMd,
            color: AppColors.PRIMARY_DARK,
          ),
        ),
        const SizedBox(width: AppSpacing.smd),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                AppStrings.PRODUCT_STOCK_TRANSFER,
                style: AppTypography.headingSmall,
              ),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                AppStrings.PRODUCT_STOCK_TRANSFER_SUBTITLE,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _TransferCard extends StatelessWidget {
  final ProductModel? source;
  final ProductModel? target;
  final num? sourceAvailableKg;
  final num? targetAvailableKg;
  final num quantityKg;
  final List<ProductModel> usableProducts;
  final List<ProductModel> targetOptions;
  final TextEditingController quantityController;
  final bool isSubmitting;
  final String? sourceError;
  final String? targetError;
  final String? quantityError;
  final ValueChanged<ProductModel> onSelectSource;
  final ValueChanged<ProductModel> onSelectTarget;
  final VoidCallback onQuantityErrorClear;
  final VoidCallback onSubmit;

  const _TransferCard({
    required this.source,
    required this.target,
    required this.sourceAvailableKg,
    required this.targetAvailableKg,
    required this.quantityKg,
    required this.usableProducts,
    required this.targetOptions,
    required this.quantityController,
    required this.isSubmitting,
    required this.sourceError,
    required this.targetError,
    required this.quantityError,
    required this.onSelectSource,
    required this.onSelectTarget,
    required this.onQuantityErrorClear,
    required this.onSubmit,
  });

  bool get _overdrawn =>
      sourceAvailableKg != null && quantityKg > sourceAvailableKg!;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.BORDER),
        boxShadow: [
          BoxShadow(
            color: AppColors.TEXT_PRIMARY.withValues(alpha: 0.04),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(AppSpacing.lg),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final bool stacked = constraints.maxWidth < 520;
                final Widget sourceTile = _ProductTile(
                  tone: _ProductTileTone.source,
                  label: AppStrings.TRANSFER_FIELD_SOURCE,
                  hint: AppStrings.TRANSFER_FIELD_SOURCE_HINT,
                  value: source,
                  items: usableProducts,
                  enabled: !isSubmitting,
                  errorText: sourceError,
                  availableKg: sourceAvailableKg,
                  onSelected: onSelectSource,
                );
                final Widget arrow = _TransferArrow(stacked: stacked);
                final Widget targetTile = _ProductTile(
                  tone: _ProductTileTone.target,
                  label: AppStrings.TRANSFER_FIELD_TARGET,
                  hint: AppStrings.TRANSFER_FIELD_TARGET_HINT,
                  value: target,
                  items: targetOptions,
                  enabled: !isSubmitting && source != null,
                  errorText: targetError,
                  availableKg: targetAvailableKg,
                  emptyHint: source == null
                      ? AppStrings.TRANSFER_FIELD_TARGET_PICK_SOURCE_FIRST
                      : AppStrings.TRANSFER_FIELD_TARGET_NONE_IN_CROP,
                  onSelected: onSelectTarget,
                );

                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      sourceTile,
                      arrow,
                      targetTile,
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: sourceTile),
                    arrow,
                    Expanded(child: targetTile),
                  ],
                );
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
              AppSpacing.lg,
            ),
            decoration: const BoxDecoration(
              color: AppColors.BACKGROUND,
              border: Border(top: BorderSide(color: AppColors.DIVIDER)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: AppTextField(
                        controller: quantityController,
                        label: AppStrings.TRANSFER_FIELD_QUANTITY_KG,
                        hint: AppStrings.TRANSFER_FIELD_QUANTITY_KG_HINT,
                        errorText: quantityError,
                        enabled: !isSubmitting,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        inputFormatters: [
                          FilteringTextInputFormatter.allow(
                            RegExp(r'^\d*\.?\d{0,3}'),
                          ),
                        ],
                        onChanged: (_) => onQuantityErrorClear(),
                      ),
                    ),
                    const SizedBox(width: AppSpacing.lg),
                    SizedBox(
                      height: AppSizes.inputHeight,
                      child: PrimaryButton(
                        label: AppStrings.TRANSFER_ACTION,
                        isLoading: isSubmitting,
                        onPressed: onSubmit,
                      ),
                    ),
                  ],
                ),
                if (_overdrawn) ...[
                  const SizedBox(height: AppSpacing.sm),
                  Row(
                    children: [
                      const Icon(
                        Icons.info_outline_rounded,
                        size: AppSizes.iconSm,
                        color: AppColors.WARNING,
                      ),
                      const SizedBox(width: AppSpacing.xs),
                      Expanded(
                        child: Text(
                          AppStrings.TRANSFER_OVERDRAWN_HINT,
                          style: AppTypography.bodySmall.copyWith(
                            color: AppColors.WARNING,
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

enum _ProductTileTone { source, target }

class _ProductTile extends StatelessWidget {
  final _ProductTileTone tone;
  final String label;
  final String hint;
  final ProductModel? value;
  final List<ProductModel> items;
  final bool enabled;
  final String? errorText;
  final String? emptyHint;
  final num? availableKg;
  final ValueChanged<ProductModel> onSelected;

  const _ProductTile({
    required this.tone,
    required this.label,
    required this.hint,
    required this.value,
    required this.items,
    required this.enabled,
    required this.errorText,
    required this.availableKg,
    this.emptyHint,
    required this.onSelected,
  });

  Color get _accent =>
      tone == _ProductTileTone.source ? AppColors.PRIMARY : AppColors.PRIMARY_DARK;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SearchableField<ProductModel>(
          label: label,
          hintText: hint,
          value: value,
          items: items,
          itemToString: (product) => product.name,
          isSame: (a, b) => a.publicId == b.publicId,
          enabled: enabled,
          errorText: errorText,
          emptyHint: emptyHint,
          onSelected: onSelected,
        ),
        const SizedBox(height: AppSpacing.smd),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 160),
          child: value == null
              ? const SizedBox(key: ValueKey('empty'), height: 0)
              : Container(
                  key: ValueKey(value!.publicId),
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.smd,
                  ),
                  decoration: BoxDecoration(
                    color: _accent.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: _accent.withValues(alpha: 0.25)),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              availableKg == null
                                  ? AppStrings.TABLE_VALUE_UNAVAILABLE
                                  : _trim(availableKg!),
                              style: AppTypography.headingMedium.copyWith(
                                color: _accent,
                              ),
                            ),
                            Text(
                              AppStrings.TRANSFER_AVAILABLE_KG_LABEL,
                              style: AppTypography.caption.copyWith(
                                color: AppColors.TEXT_SECONDARY,
                              ),
                            ),
                          ],
                        ),
                      ),
                      _CropChip(cropName: value!.cropName, accent: _accent),
                    ],
                  ),
                ),
        ),
      ],
    );
  }

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toStringAsFixed(1);
  }
}

class _CropChip extends StatelessWidget {
  final String cropName;
  final Color accent;

  const _CropChip({required this.cropName, required this.accent});

  @override
  Widget build(BuildContext context) {
    if (cropName.trim().isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        border: Border.all(color: accent.withValues(alpha: 0.4)),
      ),
      child: Text(
        cropName,
        style: AppTypography.caption.copyWith(
          color: accent,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _TransferArrow extends StatelessWidget {
  final bool stacked;

  const _TransferArrow({required this.stacked});

  @override
  Widget build(BuildContext context) {
    final Widget icon = Container(
      width: AppSizes.iconXl,
      height: AppSizes.iconXl,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.PRIMARY_SURFACE,
        shape: BoxShape.circle,
        border: Border.all(color: AppColors.PRIMARY.withValues(alpha: 0.3)),
      ),
      child: Icon(
        stacked ? Icons.arrow_downward_rounded : Icons.arrow_forward_rounded,
        size: AppSizes.iconMd,
        color: AppColors.PRIMARY_DARK,
      ),
    );

    if (stacked) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        child: Center(child: icon),
      );
    }
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xl, left: AppSpacing.md, right: AppSpacing.md),
      child: icon,
    );
  }
}

class _InfoPanel extends StatelessWidget {
  const _InfoPanel();

  static const List<(IconData, String)> _points = [
    (Icons.eco_outlined, AppStrings.TRANSFER_INFO_SAME_CROP),
    (Icons.scale_outlined, AppStrings.TRANSFER_INFO_KG_ONLY),
    (Icons.lock_clock_outlined, AppStrings.TRANSFER_INFO_IDLE_ONLY),
    (Icons.receipt_long_outlined, AppStrings.TRANSFER_INFO_LEDGER),
  ];

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: BoxDecoration(
        color: AppColors.PRIMARY_SURFACE.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.PRIMARY.withValues(alpha: 0.18)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            AppStrings.TRANSFER_INFO_TITLE,
            style: AppTypography.labelStrong,
          ),
          const SizedBox(height: AppSpacing.md),
          for (final (icon, text) in _points) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: AppSizes.iconSm, color: AppColors.PRIMARY_DARK),
                const SizedBox(width: AppSpacing.sm),
                Expanded(
                  child: Text(
                    text,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_PRIMARY,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.smd),
          ],
        ],
      ),
    );
  }
}
