import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_config.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/loaders/dots_loader.dart';
import '../../../product_packagings/data/models/product_packaging_model.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../../../products/data/models/product_model.dart';

class PickedPackaging {
  final ProductPackagingModel packaging;
  final int quantity;

  const PickedPackaging({required this.packaging, required this.quantity});
}

class OrderProductPickerDialog extends StatefulWidget {
  final ProductPackagingsRepository repository;

  /// Packagings already on the order; the backend rejects a second line for
  /// the same one, so they are shown as taken rather than offered again.
  final Set<String> existingPublicIds;

  const OrderProductPickerDialog({
    super.key,
    required this.repository,
    this.existingPublicIds = const {},
  });

  static Future<List<PickedPackaging>?> show(
    BuildContext context, {
    required ProductPackagingsRepository repository,
    Set<String> existingPublicIds = const {},
  }) {
    return showDialog<List<PickedPackaging>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => OrderProductPickerDialog(
        repository: repository,
        existingPublicIds: existingPublicIds,
      ),
    );
  }

  @override
  State<OrderProductPickerDialog> createState() =>
      _OrderProductPickerDialogState();
}

class _OrderProductPickerDialogState extends State<OrderProductPickerDialog> {
  final TextEditingController _searchController = TextEditingController();
  final Map<String, int> _quantities = {};

  List<ProductPackagingModel> _packagings = const [];
  bool _isLoading = true;
  String _search = '';

  @override
  void initState() {
    super.initState();
    _searchController.addListener(
      () => setState(() => _search = _searchController.text.trim()),
    );
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      await ProductsService.instance.loadProducts();
      final List<ProductPackagingModel> fetched = await widget.repository
          .fetchProductPackagings();
      if (!mounted) return;
      setState(() {
        _packagings = fetched;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  List<ProductPackagingModel> get _visible {
    if (_search.isEmpty) return _packagings;
    final String needle = _search.toLowerCase();
    return _packagings
        .where(
          (packaging) => packaging.productName.toLowerCase().contains(needle),
        )
        .toList();
  }

  int get _selectedCount =>
      _quantities.values.fold(0, (total, quantity) => total + quantity);

  void _notifyAlreadyAdded() {
    ToastUtils.showInfo(
      context,
      AppStrings.ORDER_PICK_ALREADY_TITLE,
      description: AppStrings.ORDER_PICK_ALREADY_BODY,
    );
  }

  void _add(ProductPackagingModel packaging) {
    setState(() {
      _quantities[packaging.publicId] =
          (_quantities[packaging.publicId] ?? 0) + 1;
    });
  }

  void _remove(ProductPackagingModel packaging) {
    setState(() {
      final int next = (_quantities[packaging.publicId] ?? 0) - 1;
      if (next <= 0) {
        _quantities.remove(packaging.publicId);
      } else {
        _quantities[packaging.publicId] = next;
      }
    });
  }

  void _confirm() {
    final List<PickedPackaging> picked = [
      for (final packaging in _packagings)
        if ((_quantities[packaging.publicId] ?? 0) > 0)
          PickedPackaging(
            packaging: packaging,
            quantity: _quantities[packaging.publicId]!,
          ),
    ];
    Navigator.of(context).pop(picked);
  }

  String get _selectionLabel {
    if (_selectedCount == 0) return AppStrings.ORDER_PICK_SELECTED_NONE;
    final String noun = _selectedCount == 1
        ? AppStrings.ORDER_PICK_SELECTED_ONE
        : AppStrings.ORDER_PICK_SELECTED_MANY;
    return '$_selectedCount $noun';
  }

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);
    final double width = (viewport.width * AppSizes.recordDialogWidthFactor)
        .clamp(0.0, AppSizes.recordDialogThreeColumnWidth);
    final double height = (viewport.height * AppSizes.recordDialogHeightFactor)
        .clamp(0.0, AppSizes.dialogMaxHeight);

    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      alignment: Alignment.topCenter,
      insetPadding: const EdgeInsets.all(AppSpacing.xxl),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: width, maxHeight: height),
        child: Container(
          width: width,
          height: height,
          clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(
            color: AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.dialog),
            border: Border.all(color: AppColors.PRIMARY),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildHeader(),
              _buildSearch(),
              Expanded(child: _buildBody()),
              _buildFooter(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      color: AppColors.PRIMARY,
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.inventory_2_outlined,
            size: AppSizes.iconXl,
            color: AppColors.WHITE,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.ORDER_PICK_PRODUCTS_TITLE,
                  style: AppTypography.titleMedium.copyWith(
                    color: AppColors.WHITE,
                  ),
                ),
                const SizedBox(height: AppSpacing.xxs),
                Text(
                  AppStrings.ORDER_PICK_PRODUCTS_SUBTITLE,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.SIDEBAR_ON_PRIMARY_MUTED,
                  ),
                ),
              ],
            ),
          ),
          MouseRegion(
            cursor: SystemMouseCursors.click,
            child: GestureDetector(
              onTap: () => Navigator.of(context).pop(),
              child: const SizedBox(
                width: AppSizes.dialogCloseTile,
                height: AppSizes.dialogCloseTile,
                child: Icon(
                  Icons.close_rounded,
                  size: AppSizes.iconLg,
                  color: AppColors.WHITE,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearch() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.lg,
        AppSpacing.md,
      ),
      child: AppTextField(
        controller: _searchController,
        hint: AppStrings.ORDER_PICK_SEARCH_HINT,
        prefixIcon: Icons.search_rounded,
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: DotsLoader(color: AppColors.PRIMARY));
    }

    final List<ProductPackagingModel> visible = _visible;
    if (visible.isEmpty) {
      return Center(
        child: Text(
          AppStrings.ORDER_PICK_EMPTY,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final int columns =
            (constraints.maxWidth / AppSizes.pickerGridMinTileWidth)
                .floor()
                .clamp(1, 4);

        return GridView.builder(
          padding: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            0,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: AppSpacing.md,
            mainAxisSpacing: AppSpacing.md,
            mainAxisExtent: AppSizes.pickerCardExtent,
          ),
          itemCount: visible.length,
          itemBuilder: (context, index) {
            final ProductPackagingModel packaging = visible[index];
            final bool isTaken = widget.existingPublicIds.contains(
              packaging.publicId,
            );

            return _PackagingCard(
              packaging: packaging,
              quantity: _quantities[packaging.publicId] ?? 0,
              isTaken: isTaken,
              onAdd: isTaken ? _notifyAlreadyAdded : () => _add(packaging),
              onRemove: () => _remove(packaging),
            );
          },
        );
      },
    );
  }

  Widget _buildFooter() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.BACKGROUND,
        border: Border(top: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              _selectionLabel,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: PrimaryButton(
              label: AppStrings.ORDER_PICK_CONFIRM,
              onPressed: _selectedCount == 0 ? null : _confirm,
            ),
          ),
        ],
      ),
    );
  }
}

class _PackagingCard extends StatelessWidget {
  final ProductPackagingModel packaging;
  final int quantity;
  final bool isTaken;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const _PackagingCard({
    required this.packaging,
    required this.quantity,
    required this.onAdd,
    required this.onRemove,
    this.isTaken = false,
  });

  ProductModel? get _product =>
      ProductsService.instance.productByPublicId(packaging.productPublicId);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.sm),
      decoration: BoxDecoration(
        color: isTaken ? AppColors.SURFACE_VARIANT : AppColors.SURFACE,
        border: Border.all(
          color: quantity > 0 ? AppColors.PRIMARY : AppColors.BORDER,
        ),
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildImagePanel(),
          const SizedBox(height: AppSpacing.sm),
          _buildDetails(),
        ],
      ),
    );
  }

  Widget _buildImagePanel() {
    final String weight = packaging.totalWeight.trim();

    return SizedBox(
      height: AppSizes.pickerCardImage + AppSizes.pickerCardStepperOverlap,
      child: Stack(
        children: [
          Positioned(
            left: 0,
            right: 0,
            top: 0,
            height: AppSizes.pickerCardImage,
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.SURFACE_VARIANT,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              clipBehavior: Clip.antiAlias,
              padding: const EdgeInsets.all(AppSpacing.sm),
              child: _buildImage(),
            ),
          ),
          if (weight.isNotEmpty)
            Positioned(
              left: AppSpacing.sm,
              top: AppSizes.pickerCardImage - AppSizes.pickerCardTagInset,
              child: _Tag(label: '$weight Kg'),
            ),
          Positioned(
            right: 0,
            bottom: 0,
            child: SizedBox(
              width: AppSizes.pickerCardStepperWidth,
              child: isTaken
                  ? _TakenPill(onTap: onAdd)
                  : _Stepper(
                      quantity: quantity,
                      onAdd: onAdd,
                      onRemove: onRemove,
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImage() {
    final String url = _resolve(_product?.imageDisplayUrl ?? '');
    if (url.isEmpty) return const Center(child: _ImageFallback());

    return Image.network(
      url,
      fit: BoxFit.contain,
      width: double.infinity,
      errorBuilder: (context, error, stack) =>
          const Center(child: _ImageFallback()),
    );
  }

  static String _resolve(String path) {
    final String trimmed = path.trim();
    if (trimmed.isEmpty) return '';
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }

    final String base = ApiConfig.baseUrl;
    if (base.isEmpty) return trimmed;
    return trimmed.startsWith('/') ? '$base$trimmed' : '$base/$trimmed';
  }

  Widget _buildDetails() {
    final ProductModel? product = _product;
    final String stage = product?.stageName ?? '';
    final num? price = packaging.sellingPriceValue;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                packaging.productName,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.bodyMedium.copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (stage.isNotEmpty) ...[
              const SizedBox(width: AppSpacing.xs),
              _StageBadge(label: stage, stageId: product?.stage?.id ?? 0),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.xxs),
        Text(
          price == null
              ? packaging.sellingPrice
              : CurrencyFormatter.rupees(price),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.bodySmall.copyWith(
            fontWeight: FontWeight.w600,
            color: AppColors.TEXT_PRIMARY,
          ),
        ),
        if (packaging.packets > 0) ...[
          const SizedBox(height: AppSpacing.xs),
          _PacketPill(
            label: '${packaging.packets} x ${packaging.packetWeight} kg',
          ),
        ],
      ],
    );
  }
}

class _TakenPill extends StatelessWidget {
  final VoidCallback onTap;

  const _TakenPill({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          height: AppSizes.pickerStepperHeight,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.SURFACE_VARIANT,
            border: Border.all(color: AppColors.BORDER_STRONG),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Text(
            AppStrings.ORDER_PICK_ON_ORDER,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.labelSmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ),
      ),
    );
  }
}

class _Stepper extends StatelessWidget {
  static const Duration _duration = Duration(milliseconds: 180);

  final int quantity;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const _Stepper({
    required this.quantity,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: AppSizes.pickerStepperHeight,
      child: AnimatedSwitcher(
        duration: _duration,
        switchInCurve: Curves.easeOutCubic,
        switchOutCurve: Curves.easeOutCubic,
        child: quantity == 0
            ? _AddButton(key: const ValueKey('add'), onTap: onAdd)
            : _CountControl(
                key: const ValueKey('count'),
                quantity: quantity,
                onAdd: onAdd,
                onRemove: onRemove,
              ),
      ),
    );
  }
}

class _AddButton extends StatelessWidget {
  final VoidCallback onTap;

  const _AddButton({super.key, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.SURFACE,
            border: Border.all(color: AppColors.PRIMARY),
            borderRadius: BorderRadius.circular(AppRadius.sm),
          ),
          child: Text(
            AppStrings.ORDER_PICK_ADD,
            style: AppTypography.button.copyWith(color: AppColors.PRIMARY),
          ),
        ),
      ),
    );
  }
}

class _CountControl extends StatelessWidget {
  final int quantity;
  final VoidCallback onAdd;
  final VoidCallback onRemove;

  const _CountControl({
    super.key,
    required this.quantity,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.PRIMARY,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _StepIcon(icon: Icons.remove_rounded, onTap: onRemove),
          Text(
            '$quantity',
            style: AppTypography.button.copyWith(
              color: AppColors.TEXT_ON_PRIMARY,
            ),
          ),
          _StepIcon(icon: Icons.add_rounded, onTap: onAdd),
        ],
      ),
    );
  }
}

class _StepIcon extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _StepIcon({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: SizedBox(
          width: AppSizes.pickerStepperHeight,
          height: AppSizes.pickerStepperHeight,
          child: Icon(
            icon,
            size: AppSizes.iconSm,
            color: AppColors.TEXT_ON_PRIMARY,
          ),
        ),
      ),
    );
  }
}

class _PacketPill extends StatelessWidget {
  final String label;

  const _PacketPill({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xs,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTypography.labelSmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
          fontWeight: FontWeight.w400,
        ),
      ),
    );
  }
}

class _StageBadge extends StatelessWidget {
  final String label;
  final int stageId;

  const _StageBadge({required this.label, required this.stageId});

  static const List<List<Color>> _palette = [
    [AppColors.ERROR, AppColors.ERROR_LIGHT],
    [AppColors.ERROR, AppColors.ERROR_LIGHT],
    [AppColors.WARNING, AppColors.WARNING_LIGHT],
    [AppColors.INFO, AppColors.INFO_LIGHT],
    [AppColors.SUCCESS, AppColors.SUCCESS_LIGHT],
  ];

  @override
  Widget build(BuildContext context) {
    final List<Color> colors = stageId >= 0 && stageId < _palette.length
        ? _palette[stageId]
        : const [AppColors.TEXT_SECONDARY, AppColors.SURFACE_VARIANT];

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xs,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: colors[1],
        borderRadius: BorderRadius.circular(AppRadius.xs),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTypography.overline.copyWith(color: colors[0]),
      ),
    );
  }
}

class _Tag extends StatelessWidget {
  final String label;

  const _Tag({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.xs,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTypography.labelSmall.copyWith(
          color: AppColors.TEXT_PRIMARY,
        ),
      ),
    );
  }
}

class _ImageFallback extends StatelessWidget {
  const _ImageFallback();

  @override
  Widget build(BuildContext context) {
    return const Icon(
      Icons.inventory_2_outlined,
      size: AppSizes.iconXxl,
      color: AppColors.TEXT_DISABLED,
    );
  }
}
