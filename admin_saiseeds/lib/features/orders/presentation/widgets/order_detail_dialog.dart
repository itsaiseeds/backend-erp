import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/constants/font_sizes.dart';
import '../../../../core/network/api_config.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/utils/validators/form_validators.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../product_packagings/data/models/product_packaging_model.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../bloc/orders_cubit.dart';
import 'order_product_picker_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/order_model.dart';
import 'order_status_badge.dart';

class OrderDetailDialog extends StatefulWidget {
  final OrderModel order;
  final RecordDialogMode initialMode;
  final ProductPackagingsRepository? packagingsRepository;

  const OrderDetailDialog({
    super.key,
    required this.order,
    this.initialMode = RecordDialogMode.view,
    this.packagingsRepository,
  });

  static Future<void> show(
    BuildContext context,
    OrderModel order, {
    required OrdersCubit cubit,
    RecordDialogMode initialMode = RecordDialogMode.view,
    ProductPackagingsRepository? packagingsRepository,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OrdersCubit>.value(
        value: cubit,
        child: OrderDetailDialog(
          order: order,
          initialMode: initialMode,
          packagingsRepository: packagingsRepository,
        ),
      ),
    );
  }

  @override
  State<OrderDetailDialog> createState() => _OrderDetailDialogState();
}

class _OrderDetailDialogState extends State<OrderDetailDialog> {
  static const List<IconData> _stepIcons = [
    Icons.summarize_outlined,
    Icons.inventory_2_outlined,
    Icons.local_shipping_outlined,
  ];

  static const List<String> _steps = [
    AppStrings.ORDER_STEP_SUMMARY,
    AppStrings.ORDER_STEP_ITEMS,
    AppStrings.ORDER_STEP_DELIVERY,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  int _stepIndex = 0;
  late RecordDialogMode _mode;
  late DateTime? _expectedDeliveryDate;
  late List<OrderPackagingModel> _lines;
  late List<TextEditingController> _quantityControllers;
  late List<TextEditingController> _priceControllers;
  bool _isSubmitting = false;

  OrderModel get _order => widget.order;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _resetDraft();
  }

  void _resetDraft() {
    _expectedDeliveryDate = _order.expectedDeliveryDate;
    _lines = List<OrderPackagingModel>.from(_order.packagings);
    _quantityControllers = _lines
        .map((line) => TextEditingController(text: '${line.quantity}'))
        .toList();
    _priceControllers = _lines
        .map(
          (line) => TextEditingController(
            text: line.effectivePrice.toStringAsFixed(
              OrderPackagingModel.PRICE_DECIMALS,
            ),
          ),
        )
        .toList();
  }

  void _disposeControllers() {
    for (final controller in _quantityControllers) {
      controller.dispose();
    }
    for (final controller in _priceControllers) {
      controller.dispose();
    }
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  void _enterEditMode() {
    if (!_order.canEdit) {
      ToastUtils.showWarning(
        context,
        AppStrings.ORDER_EDIT_LOCKED_TITLE,
        description: AppStrings.ORDER_EDIT_LOCKED_BODY,
      );
      return;
    }
    setState(() => _mode = RecordDialogMode.edit);
  }

  void _cancelEdit() {
    _disposeControllers();
    setState(() {
      _resetDraft();
      _mode = RecordDialogMode.view;
    });
  }

  Future<void> _addLine() async {
    final ProductPackagingsRepository? repository =
        widget.packagingsRepository;
    if (repository == null) return;

    final List<PickedPackaging>? picked = await OrderProductPickerDialog.show(
      context,
      repository: repository,
      existingPublicIds: {for (final line in _lines) line.publicId},
    );
    if (picked == null || picked.isEmpty || !mounted) return;

    setState(() {
      for (final PickedPackaging entry in picked) {
        final ProductPackagingModel source = entry.packaging;

        // Belt and braces: the picker already hides taken bags, but a stale
        // list must still merge rather than post a duplicate line.
        final int existing = _lines.indexWhere(
          (line) => line.publicId == source.publicId,
        );
        if (existing != -1) {
          final int merged = _lines[existing].quantity + entry.quantity;
          _lines = [..._lines];
          _lines[existing] = _lines[existing].copyWith(quantity: merged);
          _quantityControllers[existing].text = '$merged';
          continue;
        }

        _lines = [
          ..._lines,
          OrderPackagingModel(
            publicId: source.publicId,
            productPublicId: source.productPublicId,
            productName: source.productName,
            packetWeight: source.packetWeightValue ?? 0,
            packets: source.packets,
            totalWeight: source.totalWeightValue ?? 0,
            sellingPrice: source.sellingPriceValue ?? 0,
            negotiatedSellingPrice: source.sellingPriceValue ?? 0,
            quantity: entry.quantity,
          ),
        ];
        _quantityControllers = [
          ..._quantityControllers,
          TextEditingController(text: '${entry.quantity}'),
        ];
        _priceControllers = [
          ..._priceControllers,
          TextEditingController(
            text: (source.sellingPriceValue ?? 0).toStringAsFixed(
              OrderPackagingModel.PRICE_DECIMALS,
            ),
          ),
        ];
      }
    });
  }

  void _removeLine(int index) {
    setState(() {
      _lines = [..._lines]..removeAt(index);
      _quantityControllers = [..._quantityControllers];
      _priceControllers = [..._priceControllers];
      _quantityControllers.removeAt(index).dispose();
      _priceControllers.removeAt(index).dispose();
    });
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      setState(() => _stepIndex = 1);
      return;
    }

    setState(() => _isSubmitting = true);

    final OrdersCubit cubit = context.read<OrdersCubit>();
    final bool succeeded = await cubit.updateOrder(
      publicId: _order.publicId,
      changes: _buildChanges(),
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.ORDER_UPDATED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  Map<String, dynamic> _buildChanges() {
    final List<OrderPackagingModel> edited = [
      for (int index = 0; index < _lines.length; index++)
        _lines[index].copyWith(
          quantity:
              int.tryParse(_quantityControllers[index].text.trim()) ??
              _lines[index].quantity,
          negotiatedSellingPrice:
              num.tryParse(_priceControllers[index].text.trim()) ??
              _lines[index].effectivePrice,
        ),
    ];

    return {
      if (_expectedDeliveryDate != null)
        'expected_delivery_date': _dateOnly(_expectedDeliveryDate!),
      'items': [for (final line in edited) line.toEditJson()],
    };
  }

  static String _dateOnly(DateTime value) =>
      '${value.year.toString().padLeft(4, '0')}-'
      '${value.month.toString().padLeft(2, '0')}-'
      '${value.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final OrderModel order = _order;

    return AppRecordDialog(
      icon: Icons.receipt_long_outlined,
      title: AppStrings.ORDER_DETAILS_TITLE,
      subtitle: _stepSubtitle,
      mode: _mode,
      isSubmitting: _isSubmitting,
      showFooterInViewMode: true,
      extraWidth: AppSizes.recordDialogRoomyBump * 2,
      extraHeight: AppSizes.recordDialogRoomyBump * 3,
      onEdit: order.canEdit ? _enterEditMode : null,
      onCancelEdit: _isFirstStep ? _cancelEdit : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      isCancelEnabled: _isEditing || !_isFirstStep,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep
                ? (_isEditing ? _submit : null)
                : () => _goTo(_stepIndex + 1)),
      submitLabel: _isLastStep ? AppStrings.SAVE : AppStrings.STEP_NEXT,
      body: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            SectionTitle(
              title: _steps[_stepIndex],
              icon: _stepIcons[_stepIndex],
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.md),
            _buildStep(order),
          ],
        ),
      ),
    );
  }

  static const List<String> _captions = [
    AppStrings.ORDER_STEP_SUMMARY_CAPTION,
    AppStrings.ORDER_STEP_ITEMS_CAPTION,
    AppStrings.ORDER_STEP_DELIVERY_CAPTION,
  ];

  String get _stepSubtitle =>
      '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
      '${AppStrings.LABEL_SEPARATOR} ${_captions[_stepIndex]}';

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _steps.length - 1;

  /// Totals follow the draft while editing; the server's figures would still
  /// describe the order as it was fetched, which is worse than no figure.
  num get _liveTotalAmount {
    if (!_isEditing) return _order.totalAmount;
    num total = 0;
    for (int index = 0; index < _lines.length; index++) {
      final num price =
          num.tryParse(_priceControllers[index].text.trim()) ??
          _lines[index].effectivePrice;
      total += price * _lines[index].quantity;
    }
    return total;
  }

  int get _liveTotalPackets {
    if (!_isEditing) return _order.totalPackets;
    return _lines.fold(
      0,
      (total, line) => total + (line.packets * line.quantity),
    );
  }

  int get _liveItemCount =>
      _isEditing ? _lines.length : _order.itemCount;

  int get _liveBagCount => _isEditing
      ? _lines.fold(0, (total, line) => total + line.quantity)
      : _order.bagCount;

  void _goTo(int index) => setState(() => _stepIndex = index);

  Widget _buildStep(OrderModel order) {
    final Widget step = switch (_stepIndex) {
      1 => _buildItems(order),
      2 => _buildDelivery(order),
      _ => _SummaryStep(order: order, bagCount: _liveBagCount),
    };

    if (!_isLastStep) return step;

    // The closing step doubles as the order summary.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        step,
        const SizedBox(height: AppSpacing.lg),
        _OrderHeadline(
          order: order,
          totalAmount: _liveTotalAmount,
          totalPackets: _liveTotalPackets,
          itemCount: _liveItemCount,
        ),
      ],
    );
  }

  Widget _buildItems(OrderModel order) {
    if (!_isEditing) return _ItemsStep(order: order);

    if (_lines.isEmpty) {
      return Text(
        AppStrings.ORDER_NO_ITEMS,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int index = 0; index < _lines.length; index++) ...[
          if (index > 0) ...[
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.sm),
          ],
          _ItemRow(
            line: _lines[index],
            isEditable: true,
            priceController: _priceControllers[index],
            onPriceChanged: (_) => setState(() {}),
            onIncrement: () => _changeQuantity(index, 1),
            onDecrement: _lines[index].quantity <= 1
                ? null
                : () => _changeQuantity(index, -1),
            onRemove: _lines.length == 1 ? null : () => _removeLine(index),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        SecondaryButton(
          label: AppStrings.ORDER_ADD_ITEM,
          icon: Icons.add_rounded,
          onPressed: _canEdit ? _addLine : null,
        ),
      ],
    );
  }

  void _changeQuantity(int index, int delta) {
    final int next = _lines[index].quantity + delta;
    if (next < 1) return;

    setState(() {
      _lines = [..._lines];
      _lines[index] = _lines[index].copyWith(quantity: next);
      _quantityControllers[index].text = '$next';
    });
  }

  Widget _buildDelivery(OrderModel order) {
    if (!_isEditing) return _DeliveryStep(order: order);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        DetailFieldGrid(
          fields: [
            DetailField(
              label: AppStrings.ORDER_DELIVERY_ADDRESS_LABEL,
              value: order.deliveryAddress,
            ),
            DetailField(
              label: AppStrings.ORDER_CITY_LABEL,
              value: order.cityName,
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.md),
        Text(
          AppStrings.ORDER_EXPECTED_DELIVERY_LABEL,
          style: AppTypography.label,
        ),
        const SizedBox(height: AppSpacing.sm),
        SingleDateField(
          value: _expectedDeliveryDate,
          enabled: _canEdit,
          onChanged: (picked) =>
              setState(() => _expectedDeliveryDate = picked),
        ),
      ],
    );
  }
}

class _OrderHeadline extends StatelessWidget {
  final OrderModel order;
  final num totalAmount;
  final int totalPackets;
  final int itemCount;

  const _OrderHeadline({
    required this.order,
    required this.totalAmount,
    required this.totalPackets,
    required this.itemCount,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(color: AppColors.BORDER),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(AppSpacing.md),
            color: AppColors.PRIMARY_SURFACE,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        order.client.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppTypography.titleMedium,
                      ),
                      const SizedBox(height: AppSpacing.xxs),
                      Text(
                        order.publicId,
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.TEXT_SECONDARY,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: AppSpacing.sm),
                OrderStatusBadge(status: order.status),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(AppSpacing.md),
            child: Row(
              children: [
                Expanded(
                  child: _Metric(
                    value: CurrencyFormatter.rupees(totalAmount),
                    label: AppStrings.ORDER_TOTAL_AMOUNT_LABEL,
                    isEmphasised: true,
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _Metric(
                    value: '$totalPackets',
                    label: AppStrings.ORDER_TOTAL_PACKETS_LABEL,
                  ),
                ),
                const _MetricDivider(),
                Expanded(
                  child: _Metric(
                    value: '$itemCount',
                    label: AppStrings.ORDER_ITEM_COUNT_LABEL,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  final String value;
  final String label;
  final bool isEmphasised;

  const _Metric({
    required this.value,
    required this.label,
    this.isEmphasised = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.titleMedium.copyWith(
            color: isEmphasised ? AppColors.PRIMARY : AppColors.TEXT_PRIMARY,
          ),
        ),
        const SizedBox(height: AppSpacing.xxs),
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
      ],
    );
  }
}

class _MetricDivider extends StatelessWidget {
  const _MetricDivider();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: AppSizes.borderThin,
      height: AppSizes.orderMetricDividerHeight,
      color: AppColors.BORDER,
    );
  }
}

class _SummaryStep extends StatelessWidget {
  final OrderModel order;
  final int bagCount;

  const _SummaryStep({required this.order, required this.bagCount});

  @override
  Widget build(BuildContext context) {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.ORDER_BAG_COUNT_LABEL,
          value: '$bagCount',
        ),
        DetailField(
          label: AppStrings.ORDER_PLACED_ON_LABEL,
          value: DateFormatter.instantLabel(order.createdAt),
        ),
        DetailField(
          label: AppStrings.ORDER_PLACED_BY_LABEL,
          value: order.createdBy,
        ),
        DetailField(
          label: AppStrings.ORDER_CLIENT_ONBOARDED_BY_LABEL,
          value: order.clientCreatedBy,
        ),
        DetailField(
          label: AppStrings.ORDER_VERIFIED_BY_LABEL,
          value: order.verifiedBy.trim().isEmpty
              ? AppStrings.ORDER_AWAITING_VERIFICATION
              : order.verifiedBy,
        ),
      ],
    );
  }
}

class _ItemsStep extends StatelessWidget {
  final OrderModel order;

  const _ItemsStep({required this.order});

  @override
  Widget build(BuildContext context) {
    if (order.packagings.isEmpty) {
      return Text(
        AppStrings.ORDER_NO_ITEMS,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int index = 0; index < order.packagings.length; index++) ...[
          if (index > 0) ...[
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.sm),
          ],
          _ItemRow(line: order.packagings[index]),
        ],
      ],
    );
  }
}

class _ItemRow extends StatelessWidget {
  final OrderPackagingModel line;
  final bool isEditable;
  final TextEditingController? priceController;
  final ValueChanged<String>? onPriceChanged;
  final VoidCallback? onIncrement;
  final VoidCallback? onDecrement;
  final VoidCallback? onRemove;

  const _ItemRow({
    required this.line,
    this.isEditable = false,
    this.priceController,
    this.onPriceChanged,
    this.onIncrement,
    this.onDecrement,
    this.onRemove,
  });

  /// While editing, the typed price wins over the fetched one.
  num get _lineTotal {
    if (!isEditable || priceController == null) return line.lineTotal;
    final num price =
        num.tryParse(priceController!.text.trim()) ?? line.effectivePrice;
    return price * line.quantity;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Thumbnail(url: line.imageUrl),
            const SizedBox(width: AppSpacing.smd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    line.productName,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xs),
                  Wrap(
                    spacing: AppSpacing.xs,
                    runSpacing: AppSpacing.xs,
                    children: [
                      _PackChip(label: line.packetSummary),
                      _PackChip(label: line.totalWeightSummary),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            if (isEditable)
              _QuantityStepper(
                quantity: line.quantity,
                onIncrement: onIncrement,
                onDecrement: onDecrement,
              )
            else
              _QuantityPill(quantity: line.quantity),
            if (isEditable && onRemove != null) ...[
              const SizedBox(width: AppSpacing.sm),
              IconActionButton(
                icon: Icons.delete_outline_rounded,
                tooltip: AppStrings.ORDER_REMOVE_ITEM,
                type: IconActionType.error,
                onPressed: onRemove,
              ),
            ],
          ],
        ),
        const SizedBox(height: AppSpacing.sm),
        Row(
          children: [
            Expanded(
              child: isEditable
                  ? _PriceInput(
                      controller: priceController!,
                      onChanged: onPriceChanged,
                    )
                  : Row(
                children: [
                  Text(
                    CurrencyFormatter.rupees(line.effectivePrice),
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_PRIMARY,
                    ),
                  ),
                  const SizedBox(width: AppSpacing.xxs),
                  Text(
                    AppStrings.ORDER_PER_BAG,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_DISABLED,
                    ),
                  ),
                  if (line.isNegotiated) ...[
                    const SizedBox(width: AppSpacing.xs),
                    Text(
                      CurrencyFormatter.rupees(line.sellingPrice),
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.TEXT_DISABLED,
                        decoration: TextDecoration.lineThrough,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            Text(
              CurrencyFormatter.rupees(_lineTotal),
              style: AppTypography.bodyMedium.copyWith(
                color: AppColors.PRIMARY,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _QuantityStepper extends StatelessWidget {
  final int quantity;
  final VoidCallback? onIncrement;
  final VoidCallback? onDecrement;

  const _QuantityStepper({
    required this.quantity,
    required this.onIncrement,
    required this.onDecrement,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: AppSizes.orderStepperHeight,
      decoration: BoxDecoration(
        color: AppColors.PRIMARY,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _StepIcon(icon: Icons.remove_rounded, onTap: onDecrement),
          Container(
            constraints: const BoxConstraints(
              minWidth: AppSizes.orderStepperCountWidth,
            ),
            alignment: Alignment.center,
            child: Text(
              '$quantity',
              style: AppTypography.button.copyWith(
                color: AppColors.TEXT_ON_PRIMARY,
              ),
            ),
          ),
          _StepIcon(icon: Icons.add_rounded, onTap: onIncrement),
        ],
      ),
    );
  }
}

class _StepIcon extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _StepIcon({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final bool isEnabled = onTap != null;

    return MouseRegion(
      cursor: isEnabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: onTap,
        child: SizedBox(
          width: AppSizes.orderStepperHeight,
          height: AppSizes.orderStepperHeight,
          child: Icon(
            icon,
            size: AppSizes.iconSm,
            color: isEnabled
                ? AppColors.TEXT_ON_PRIMARY
                : AppColors.SIDEBAR_ON_PRIMARY_MUTED,
          ),
        ),
      ),
    );
  }
}

class _PriceInput extends StatelessWidget {
  final TextEditingController controller;
  final ValueChanged<String>? onChanged;

  const _PriceInput({required this.controller, this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        SizedBox(
          width: AppSizes.orderPriceFieldWidth,
          child: AppTextField(
            controller: controller,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            onChanged: onChanged,
            validator: FormValidators.nonNegativeAmount,
          ),
        ),
        const SizedBox(width: AppSpacing.xs),
        Text(
          AppStrings.ORDER_PER_BAG,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
        ),
      ],
    );
  }
}

class _PackChip extends StatelessWidget {
  final String label;

  const _PackChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(color: AppColors.PRIMARY),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        label,
        style: AppTypography.bodySmall.copyWith(color: AppColors.TEXT_PRIMARY),
      ),
    );
  }
}

class _QuantityPill extends StatelessWidget {
  final int quantity;

  const _QuantityPill({required this.quantity});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.sm,
        vertical: AppSpacing.xxs,
      ),
      decoration: BoxDecoration(
        color: AppColors.PRIMARY_SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Text(
        '${AppStrings.ORDER_QUANTITY_PREFIX} $quantity',
        style: AppTypography.bodySmall.copyWith(color: AppColors.PRIMARY),
      ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  static const double _size = 44;

  final String url;

  const _Thumbnail({required this.url});

  @override
  Widget build(BuildContext context) {
    final String resolved = _resolve(url);

    return Container(
      width: _size,
      height: _size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppSpacing.xs),
      ),
      clipBehavior: Clip.antiAlias,
      child: resolved.isEmpty
          ? const Icon(
              Icons.inventory_2_outlined,
              size: AppFontSizes.FONT_18,
              color: AppColors.TEXT_DISABLED,
            )
          : Image.network(
              resolved,
              fit: BoxFit.cover,
              errorBuilder: (context, error, stack) => const Icon(
                Icons.inventory_2_outlined,
                size: AppFontSizes.FONT_18,
                color: AppColors.TEXT_DISABLED,
              ),
            ),
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
}

class _DeliveryStep extends StatelessWidget {
  final OrderModel order;

  const _DeliveryStep({required this.order});

  @override
  Widget build(BuildContext context) {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.ORDER_DELIVERY_ADDRESS_LABEL,
          value: order.deliveryAddress,
        ),
        DetailField(label: AppStrings.ORDER_CITY_LABEL, value: order.cityName),
        DetailField(
          label: AppStrings.ORDER_DISPATCH_MODE_LABEL,
          value: order.isAgencyDispatch
              ? AppStrings.ORDER_DISPATCH_AGENCY
              : AppStrings.ORDER_DISPATCH_PRIVATE,
        ),
        DetailField(
          label: AppStrings.ORDER_TRANSPORT_AGENCY_LABEL,
          value: order.agencyName.trim().isEmpty
              ? AppStrings.ORDER_DISPATCH_PRIVATE
              : order.agencyName,
        ),
        DetailField(
          label: AppStrings.ORDER_EXPECTED_DELIVERY_LABEL,
          value: DateFormatter.dayLabel(order.expectedDeliveryDate),
        ),
      ],
    );
  }
}
