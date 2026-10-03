import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../../orders/presentation/widgets/order_status_badge.dart';
import '../../data/models/custom_order_model.dart';
import '../../../product_packagings/data/models/product_packaging_model.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../../../orders/presentation/widgets/order_product_picker_dialog.dart';
import '../bloc/custom_orders_cubit.dart';
import 'custom_order_line_row.dart';

/// Views and edits a custom order over the same three steps as a regular one.
class CustomOrderDetailDialog extends StatefulWidget {
  final CustomOrderModel order;
  final RecordDialogMode initialMode;

  const CustomOrderDetailDialog({
    super.key,
    required this.order,
    this.initialMode = RecordDialogMode.view,
  });

  static final DateFormat isoDate = DateFormat('yyyy-MM-dd');

  static Future<void> show(
    BuildContext context, {
    required CustomOrdersCubit cubit,
    required CustomOrderModel order,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<CustomOrdersCubit>.value(
        value: cubit,
        child: CustomOrderDetailDialog(
          order: order,
          initialMode: initialMode,
        ),
      ),
    );
  }

  @override
  State<CustomOrderDetailDialog> createState() =>
      _CustomOrderDetailDialogState();
}

class _CustomOrderDetailDialogState extends State<CustomOrderDetailDialog> {
  static const List<IconData> _ICONS = [
    Icons.summarize_outlined,
    Icons.inventory_2_outlined,
    Icons.local_shipping_outlined,
  ];

  static const List<String> _STEPS = [
    AppStrings.ORDER_STEP_SUMMARY,
    AppStrings.ORDER_STEP_ITEMS,
    AppStrings.ORDER_STEP_DELIVERY,
  ];

  static const List<String> _CAPTIONS = [
    AppStrings.ORDER_STEP_SUMMARY_CAPTION,
    AppStrings.ORDER_STEP_ITEMS_CAPTION,
    AppStrings.ORDER_STEP_DELIVERY_CAPTION,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _commentsController = TextEditingController();

  int _stepIndex = 0;
  late RecordDialogMode _mode;
  late List<CustomOrderLine> _lines;
  DateTime? _expectedDelivery;
  bool _isSubmitting = false;
  String? _linesError;

  CustomOrderModel get _order => widget.order;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _isEditing && !_isSubmitting;

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _resetDraft();
    _loadCatalogue();
  }

  /// The picker needs the catalogue, so it is fetched when the dialog opens
  /// rather than on tab entry.
  Future<void> _loadCatalogue() async {
    await Future.wait([
      ProductsService.instance.loadProducts(),
      PackagingsService.instance.loadPackagings(),
    ]);
    if (mounted) setState(() {});
  }


  void _resetDraft() {
    _commentsController.text = _order.specialComments;
    _expectedDelivery = _order.expectedDeliveryDateTime;
    _lines = [
      for (final CustomOrderItemModel item in _order.items)
        CustomOrderLine(
          product: ProductsService.instance.productByPublicId(
            item.productPublicId,
          ),
          productPublicId: item.productPublicId,
          productName: item.productName,
          imageUrl: item.imageUrl,
          packetWeight: item.packetWeight,
          packets: item.packets,
          priceText: item.negotiatedSellingPrice,
        ),
    ];
  }

  @override
  void dispose() {
    _commentsController.dispose();
    for (final CustomOrderLine line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  void _enterEditMode() => setState(() => _mode = RecordDialogMode.edit);

  void _cancelEdit() {
    setState(() {
      for (final CustomOrderLine line in _lines) {
        line.dispose();
      }
      _resetDraft();
      _linesError = null;
      _mode = RecordDialogMode.view;
    });
  }

  void _goTo(int index) =>
      setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));

  /// Opens the product grid and appends what was chosen. A packaging already
  /// on the order merges into its line rather than posting a duplicate.
  Future<void> _addLine() async {
    final List<PickedPackaging>? picked = await OrderProductPickerDialog.show(
      context,
      repository: ProductPackagingsRepository(
        apiClient: context.read<ApiClient>(),
      ),
      existingPublicIds: {for (final CustomOrderLine line in _lines) line.key},
      isPerPacket: true,
    );
    if (picked == null || picked.isEmpty || !mounted) return;

    setState(() {
      for (final PickedPackaging entry in picked) {
        final ProductPackagingModel source = entry.packaging;
        final String key = '${source.productPublicId}|${source.packetWeight}';

        final int existing = _lines.indexWhere((line) => line.key == key);
        if (existing != -1) {
          _lines[existing].packets += entry.quantity;
          continue;
        }

        _lines = [
          ..._lines,
          CustomOrderLine(
            product: ProductsService.instance.productByPublicId(
              source.productPublicId,
            ),
            productPublicId: source.productPublicId,
            productName: source.productName,
            imageUrl:
                ProductsService.instance
                    .productByPublicId(source.productPublicId)
                    ?.imageUrl ??
                '',
            packetWeight: source.packetWeight,
            packetsPerBag: source.packets,
            packets: entry.quantity,
            priceText: _packetPriceOf(source),
          ),
        ];
      }
    });
  }

  /// A bag's price divided by what it holds: a custom order line is priced
  /// per packet, but the API only publishes the bag price.
  static String _packetPriceOf(ProductPackagingModel packaging) {
    final num? bagPrice = packaging.sellingPriceValue;
    if (bagPrice == null || packaging.packets <= 0) {
      return packaging.sellingPrice;
    }
    return (bagPrice / packaging.packets).toStringAsFixed(2);
  }

  void _removeLine(int index) {
    setState(() {
      final List<CustomOrderLine> next = [..._lines];
      next.removeAt(index).dispose();
      _lines = next;
    });
  }

  void _changePackets(int index, int delta) {
    final int next = _lines[index].packets + delta;
    if (next < 1) return;
    setState(() => _lines[index].packets = next);
  }

  num get _liveTotalAmount =>
      _lines.fold<num>(0, (sum, line) => sum + line.lineTotal);

  int get _liveTotalPackets =>
      _lines.fold<int>(0, (sum, line) => sum + line.packets);

  Future<void> _submit() async {
    final bool formValid = _formKey.currentState?.validate() ?? false;
    final bool linesValid =
        _lines.isNotEmpty && _lines.every((line) => line.isValid);

    setState(
      () => _linesError = linesValid
          ? null
          : AppStrings.CUSTOM_ORDER_LINE_INVALID,
    );

    if (!formValid || !linesValid) {
      setState(() => _stepIndex = 1);
      return;
    }

    setState(() => _isSubmitting = true);
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

    final bool succeeded = await cubit.updateCustomOrder(
      publicId: _order.publicId,
      changes: {
        'special_comments': _commentsController.text.trim(),
        if (_expectedDelivery != null)
          'expected_delivery_date': CustomOrderDetailDialog.isoDate.format(
            _expectedDelivery!,
          ),
        'items': [for (final CustomOrderLine line in _lines) line.toJson()],
      },
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.CUSTOM_ORDER_UPDATED);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.tune_outlined,
      title: AppStrings.CUSTOM_ORDER_DETAIL_TITLE,
      subtitle: _subtitle,
      mode: _mode,
      isSubmitting: _isSubmitting,
      showFooterInViewMode: true,
      extraWidth: AppSizes.recordDialogRoomyBump * 2,
      extraHeight: AppSizes.recordDialogRoomyBump * 3,
      badge: OrderStatusBadge(status: _order.statusValue),
      onEdit: _enterEditMode,
      onCancelEdit: _isFirstStep ? _cancelEdit : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      isCancelEnabled: _isEditing || !_isFirstStep,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep
                ? (_isEditing ? _submit : null)
                : () => _goTo(_stepIndex + 1)),
      submitLabel: _isLastStep ? AppStrings.UPDATE : AppStrings.STEP_NEXT,
      body: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            SectionTitle(
              title: _STEPS[_stepIndex],
              icon: _ICONS[_stepIndex],
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildStep(),
          ],
        ),
      ),
    );
  }

  String get _subtitle =>
      '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
      '${AppStrings.LABEL_SEPARATOR} ${_CAPTIONS[_stepIndex]}';

  Widget _buildStep() {
    switch (_stepIndex) {
      case 1:
        return _buildItems();
      case 2:
        return _buildDelivery();
      default:
        return _buildSummary();
    }
  }

  Widget _buildSummary() {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.COLUMN_ORDER_ID,
          value: _order.publicId,
        ),
        DetailField(
          label: AppStrings.COLUMN_ORDER_CLIENT,
          value: _order.clientName,
        ),
        DetailField(
          label: AppStrings.COLUMN_ORDER_AMOUNT,
          value: CurrencyFormatter.rupees(_liveTotalAmount),
        ),
        DetailField(
          label: AppStrings.COLUMN_CUSTOM_ORDER_PACKETS,
          value: '$_liveTotalPackets',
        ),
        DetailField(
          label: AppStrings.COLUMN_ORDER_SALES_PERSON,
          value: _order.createdBy,
        ),
        DetailField(
          label: AppStrings.COLUMN_ORDER_PLACED,
          value: DateFormatter.instantLabel(_order.createdAtDateTime),
        ),
      ],
    );
  }

  Widget _buildItems() {
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
          _buildLine(index),
        ],
        if (_isEditing) ...[
          const SizedBox(height: AppSpacing.md),
          SecondaryButton(
            label: AppStrings.ORDER_ADD_ITEM,
            icon: Icons.add_rounded,
            onPressed: _canEdit ? _addLine : null,
          ),
        ],
        if (_linesError != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            _linesError!,
            style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
          ),
        ],
      ],
    );
  }

  Widget _buildLine(int index) {
    final CustomOrderLine line = _lines[index];

    return CustomOrderLineRow(
      line: line,
      isEditable: _isEditing,
      onIncrement: _canEdit ? () => _changePackets(index, 1) : null,
      onDecrement: !_canEdit || line.packets <= 1
          ? null
          : () => _changePackets(index, -1),
      onRemove: _canEdit ? () => _removeLine(index) : null,
      onPriceChanged: (_) => setState(() {}),
    );
  }

  Widget _buildDelivery() {
    if (!_isEditing) {
      return DetailFieldGrid(
        fields: [
          DetailField(
            label: AppStrings.FIELD_DELIVERY_ADDRESS_PICK,
            value: _order.deliveryAddress,
          ),
          DetailField(
            label: AppStrings.COLUMN_CUSTOM_ORDER_CITY,
            value: _order.cityName,
          ),
          DetailField(
            label: AppStrings.FIELD_EXPECTED_DELIVERY,
            value: DateFormatter.dayLabel(_order.expectedDeliveryDateTime),
          ),
          DetailField(
            label: AppStrings.FIELD_SPECIAL_COMMENTS,
            value: _order.specialComments,
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SingleDateField(
          label: AppStrings.FIELD_EXPECTED_DELIVERY,
          value: _expectedDelivery,
          enabled: _canEdit,
          onChanged: (date) => setState(() => _expectedDelivery = date),
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextField(
          controller: _commentsController,
          label: AppStrings.FIELD_SPECIAL_COMMENTS,
          hint: AppStrings.FIELD_SPECIAL_COMMENTS_HINT,
          enabled: _canEdit,
        ),
      ],
    );
  }
}
