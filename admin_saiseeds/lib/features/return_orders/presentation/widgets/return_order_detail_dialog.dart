import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/return_order_edit_model.dart';
import '../../data/models/return_order_model.dart';
import '../../data/models/return_order_status.dart';
import '../../data/return_orders_repository.dart';
import '../../../orders/data/models/order_status.dart';
import 'return_order_status_badge.dart';

/// One return, read-only or being edited, in the same three-step shell the
/// order dialog uses: Summary -> Items -> Review.
///
/// The header pencil flips this dialog into edit mode exactly the way the
/// order dialog does, so the table only needs a view action; the row's Edit
/// action simply opens the same dialog with [RecordDialogMode.edit].
///
/// The API replaces the whole return on every save, so the editor is
/// deliberately not a diff editor: it holds the complete set of lines, shows
/// what is about to be deleted, and sends all of it. Editing product, packet
/// weight or line identity is not offered because those come from the challan
/// -- changing them here would let the return describe stock the order never
/// had.
class ReturnOrderDetailDialog extends StatefulWidget {
  final ReturnOrderModel returnOrder;
  final ReturnOrdersRepository? repository;
  final RecordDialogMode initialMode;

  const ReturnOrderDetailDialog({
    super.key,
    required this.returnOrder,
    this.repository,
    this.initialMode = RecordDialogMode.view,
  });

  /// Returns `true` when the dialog was closed because a save succeeded.
  static Future<bool> show(
    BuildContext context,
    ReturnOrderModel returnOrder, {
    ReturnOrdersRepository? repository,
    RecordDialogMode initialMode = RecordDialogMode.view,
  }) async {
    final bool? saved = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ReturnOrderDetailDialog(
        returnOrder: returnOrder,
        repository: repository,
        initialMode: initialMode,
      ),
    );
    return saved ?? false;
  }

  @override
  State<ReturnOrderDetailDialog> createState() =>
      _ReturnOrderDetailDialogState();
}

class _ReturnOrderDetailDialogState extends State<ReturnOrderDetailDialog> {
  static const List<IconData> _stepIcons = [
    Icons.summarize_outlined,
    Icons.inventory_2_outlined,
    Icons.fact_check_outlined,
  ];

  static const List<String> _steps = [
    AppStrings.RETURN_ORDER_STEP_SUMMARY,
    AppStrings.RETURN_ORDER_STEP_ITEMS,
    AppStrings.RETURN_ORDER_STEP_REVIEW,
  ];

  static const List<String> _captions = [
    AppStrings.RETURN_ORDER_STEP_SUMMARY_CAPTION,
    AppStrings.RETURN_ORDER_STEP_ITEMS_CAPTION,
    AppStrings.RETURN_ORDER_STEP_REVIEW_CAPTION,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  int _stepIndex = 0;
  late RecordDialogMode _mode;
  late DateTime? _returnDate;

  /// Kept in sync with [_controllers] by index; see [_removeLine].
  late List<ReturnOrderItemEditModel> _lines;
  late List<TextEditingController> _packetControllers;
  late List<TextEditingController> _priceControllers;

  /// Lines the admin has removed but not yet saved. Held apart from the live
  /// list so the review step can say what saving will cost before it happens.
  final List<ReturnOrderItemEditModel> _removed = [];

  bool _isSubmitting = false;
  String? _error;

  ReturnOrderModel get _order => widget.returnOrder;

  bool get _isEditing => _mode == RecordDialogMode.edit;

  bool get _canEdit => _order.canEdit && widget.repository != null;

  @override
  void initState() {
    super.initState();
    _mode = widget.initialMode;
    _resetDraft();
  }

  void _resetDraft() {
    _returnDate = _order.returnDate;
    _lines = _order.items
        .map(ReturnOrderItemEditModel.fromItem)
        .toList(growable: true);
    _packetControllers = _lines.map(_packetController).toList();
    _priceControllers = _lines.map(_priceController).toList();
    _removed.clear();
    _error = null;
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  void _disposeControllers() {
    for (final controller in _packetControllers) {
      controller.dispose();
    }
    for (final controller in _priceControllers) {
      controller.dispose();
    }
  }

  TextEditingController _packetController(ReturnOrderItemEditModel line) {
    return TextEditingController(text: '${line.packets}')
      ..addListener(_revalidate);
  }

  TextEditingController _priceController(ReturnOrderItemEditModel line) {
    return TextEditingController(
      text: line.pricePerPacket == line.pricePerPacket.roundToDouble()
          ? line.pricePerPacket.toInt().toString()
          : line.pricePerPacket.toString(),
    )..addListener(_revalidate);
  }

  /// Totals move as the admin types, so the figure under the fields has to keep
  /// up without a full submit attempt in between.
  void _revalidate() => setState(() {});

  void _enterEditMode() {
    if (!_canEdit) return;
    setState(() => _mode = RecordDialogMode.edit);
  }

  void _cancelEdit() {
    _disposeControllers();
    setState(() {
      _resetDraft();
      _mode = RecordDialogMode.view;
    });
  }

  void _removeLine(int index) {
    setState(() {
      _removed.add(_lines.removeAt(index));
      _packetControllers.removeAt(index).dispose();
      _priceControllers.removeAt(index).dispose();
    });
  }

  void _restoreLine(int index) {
    setState(() {
      final ReturnOrderItemEditModel line = _removed.removeAt(index);
      _lines.add(line);
      _packetControllers.add(_packetController(line));
      _priceControllers.add(_priceController(line));
    });
  }

  void _goTo(int index) => setState(() => _stepIndex = index);

  /// Leaving the items step is the only place the line fields exist in the
  /// tree, so that is where they are checked -- otherwise the review step
  /// could save a line whose packets were cleared on the way past.
  void _goToNext() {
    if (_stepIndex == 1 && !(_formKey.currentState?.validate() ?? false)) {
      return;
    }
    setState(() => _stepIndex += 1);
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) {
      setState(() => _stepIndex = 1);
      return;
    }

    final ReturnOrdersRepository? repository = widget.repository;
    if (repository == null) return;

    final List<ReturnOrderItemEditModel> items = [
      for (int index = 0; index < _lines.length; index++)
        _lines[index].copyWith(
          packets: int.tryParse(_packetControllers[index].text.trim()) ??
              _lines[index].packets,
          pricePerPacket:
              num.tryParse(_priceControllers[index].text.trim()) ??
                  _lines[index].pricePerPacket,
        ),
    ];

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await repository.updateReturn(
        publicId: _order.publicId,
        request: ReturnOrderEditRequest(returnDate: _returnDate, items: items),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSubmitting = false;
        _error = '$e';
      });
      return;
    }

    if (!mounted) return;
    Navigator.of(context).pop(true);
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.assignment_return_outlined,
      title: AppStrings.RETURN_ORDER_DETAILS_TITLE,
      subtitle: _stepSubtitle,
      mode: _mode,
      isTall: true,
      isSubmitting: _isSubmitting,
      showFooterInViewMode: true,
      badge: ReturnOrderStatusBadge(status: _order.status),
      onEdit: _canEdit ? _enterEditMode : null,
      onCancelEdit: _isFirstStep ? _cancelEdit : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      isCancelEnabled: _isEditing || !_isFirstStep,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep
                ? (_isEditing ? _submit : null)
                : _goToNext),
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
            _buildStep(),
          ],
        ),
      ),
    );
  }

  String get _stepSubtitle =>
      '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
      '${AppStrings.LABEL_SEPARATOR} ${_captions[_stepIndex]}';

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _steps.length - 1;

  Widget _buildStep() {
    final Widget step = switch (_stepIndex) {
      1 => _isEditing ? _buildItemsEdit() : _buildItemsView(),
      2 => _isEditing ? _buildReviewEdit() : _buildReviewView(),
      _ => _isEditing ? _buildSummaryEdit() : _buildSummaryView(),
    };

    if (!_isLastStep) return step;

    // The closing step doubles as the return's headline.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        step,
        if (_isEditing) ...[
          const SizedBox(height: AppSpacing.md),
          const AppHairline(),
          const SizedBox(height: AppSpacing.md),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.md),
              child: Text(
                _error!,
                style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
              ),
            ),
        ],
        const SizedBox(height: AppSpacing.lg),
        _TotalsRow(
          packets: _livePackets,
          kg: _liveKg,
          amount: _liveAmount,
        ),
      ],
    );
  }

  // -------------------------------------------------------------------------
  // Summary
  // -------------------------------------------------------------------------

  Widget _buildSummaryView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        DetailFieldGrid(fields: _identityFields()),
        if (_decisionOf(_order) != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(
            _decisionOf(_order)!,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildSummaryEdit() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.RETURN_ORDER_EDIT_REPLACEMENT_WARNING,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        SingleDateField(
          label: AppStrings.RETURN_ORDER_EDIT_DATE,
          value: _returnDate,
          onChanged: (DateTime? value) =>
              setState(() => _returnDate = value),
        ),
        const SizedBox(height: AppSpacing.md),
        const AppHairline(),
        const SizedBox(height: AppSpacing.md),
        DetailFieldGrid(fields: _identityFields()),
      ],
    );
  }

  List<DetailField> _identityFields() => [
    DetailField(
      label: AppStrings.COLUMN_RETURN_CLIENT,
      value: _order.client.companyName,
    ),
    DetailField(
      label: AppStrings.COLUMN_RETURN_ORDER,
      value: _order.order.publicId,
    ),
    DetailField(
      label: AppStrings.RETURN_ORDER_ORDER_STATUS,
      value: OrderStatusX.labelOf(
        OrderStatusX.fromRaw(_order.order.status),
      ),
    ),
    DetailField(
      label: AppStrings.RETURN_ORDER_EDIT_DATE,
      value: DateFormatter.label(_isoDate(_order.returnDate)),
    ),
    DetailField(
      label: AppStrings.COLUMN_RETURN_RAISED_BY,
      value: _order.createdByName,
    ),
    DetailField(
      label: AppStrings.DETAIL_FIELD_CREATED_AT,
      value: DateFormatter.instantLabel(_order.createdAt),
    ),
  ];

  // -------------------------------------------------------------------------
  // Items
  // -------------------------------------------------------------------------

  Widget _buildItemsView() {
    if (_order.items.isEmpty) {
      return Text(
        AppStrings.TABLE_VALUE_UNAVAILABLE,
        style: AppTypography.bodySmall.copyWith(color: AppColors.TEXT_SECONDARY),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SectionTitle(
          title: _itemsLabel,
          icon: Icons.inventory_2_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.md),
        for (int index = 0; index < _order.items.length; index++) ...[
          if (index > 0) ...[
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.sm),
          ],
          _ReadOnlyItemRow(_order.items[index]),
        ],
      ],
    );
  }

  Widget _buildItemsEdit() {
    if (_lines.isEmpty) {
      return Text(
        AppStrings.RETURN_ORDER_EDIT_EMPTY,
        style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SectionTitle(
          title: _itemsLabel,
          icon: Icons.inventory_2_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.md),
        for (int index = 0; index < _lines.length; index++)
          _LineEditor(
            key: ValueKey('${_lines[index].product.publicId}#index'),
            line: _lines[index],
            packetController: _packetControllers[index],
            priceController: _priceControllers[index],
            canRemove: _lines.length > 1,
            onRemove: () => _removeLine(index),
          ),
      ],
    );
  }

  // -------------------------------------------------------------------------
  // Review
  // -------------------------------------------------------------------------

  Widget _buildReviewView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_decisionOf(_order) != null)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              _decisionOf(_order)!,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
        if (_hasInwardLots) ...[
          SectionTitle(
            title: AppStrings.RETURN_ORDER_INWARD_LOTS,
            icon: Icons.warehouse_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _LotList(
            label: AppStrings.RETURN_ORDER_INWARD_RAW_TITLE,
            lots: _order.inwardRawMaterials,
          ),
          _LotList(
            label: AppStrings.RETURN_ORDER_INWARD_OTHER_TITLE,
            lots: _order.inwardOtherMaterials,
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            _order.includeInOtherRawMaterials == true
                ? AppStrings.RETURN_ORDER_MATERIALS_BOOKED_YES
                : AppStrings.RETURN_ORDER_MATERIALS_BOOKED_NO,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildReviewEdit() {
    if (_removed.isEmpty) {
      return Text(
        AppStrings.RETURN_ORDER_EDIT_NOTHING_DROPPED,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return _RemovedLines(removed: _removed, onRestore: _restoreLine);
  }

  // -------------------------------------------------------------------------
  // Totals
  // -------------------------------------------------------------------------

  /// Totals follow the draft while editing; the server's figures would still
  /// describe the return as it was fetched, which is worse than no figure.
  num get _liveKg {
    if (!_isEditing) return _order.totalKg;
    num total = 0;
    for (int index = 0; index < _lines.length; index++) {
      total += _lineKg(index);
    }
    return total;
  }

  num get _liveAmount {
    if (!_isEditing) return _order.totalAmount;
    num total = 0;
    for (int index = 0; index < _lines.length; index++) {
      total += _lineAmount(index);
    }
    return total;
  }

  num _lineKg(int index) {
    final int packets =
        int.tryParse(_packetControllers[index].text.trim()) ??
            _lines[index].packets;
    return _lines[index].packetWeight * packets;
  }

  num _lineAmount(int index) {
    final int packets =
        int.tryParse(_packetControllers[index].text.trim()) ??
            _lines[index].packets;
    final num price =
        num.tryParse(_priceControllers[index].text.trim()) ??
            _lines[index].pricePerPacket;
    return price * packets;
  }

  int get _livePackets {
    if (!_isEditing) return _order.totalPackets;
    int total = 0;
    for (final controller in _packetControllers) {
      total += int.tryParse(controller.text.trim()) ?? 0;
    }
    return total;
  }

  bool get _hasInwardLots =>
      _order.inwardRawMaterials.isNotEmpty ||
      _order.inwardOtherMaterials.isNotEmpty;

  String get _itemsLabel {
    final int count = _isEditing ? _lines.length : _order.items.length;
    return count == 1
        ? AppStrings.RETURN_ORDER_ITEMS_TITLE_ONE
        : AppStrings.RETURN_ORDER_ITEMS_TITLE_MANY.replaceAll('%s', '$count');
  }

  /// Who last acted on the return, and what they decided.
  static String? _decisionOf(ReturnOrderModel order) {
    switch (order.status) {
      case ReturnOrderStatus.accepted:
        return AppStrings.RETURN_ORDER_ACCEPTED_BY.replaceAll(
          '%s',
          order.verifiedByName,
        );
      case ReturnOrderStatus.rejected:
        return AppStrings.RETURN_ORDER_REJECTED_BY.replaceAll(
          '%s',
          order.rejectedByName,
        );
      case ReturnOrderStatus.pending:
      case ReturnOrderStatus.unknown:
        return null;
    }
  }

  static String _isoDate(DateTime? value) {
    if (value == null) return '';
    final String month = value.month.toString().padLeft(2, '0');
    final String day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }
}

class _LineEditor extends StatelessWidget {
  final ReturnOrderItemEditModel line;
  final TextEditingController packetController;
  final TextEditingController priceController;
  final bool canRemove;
  final VoidCallback onRemove;

  const _LineEditor({
    super.key,
    required this.line,
    required this.packetController,
    required this.priceController,
    required this.canRemove,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.md),
      child: Row(
        // One line per return: product detail, both fields and the remove
        // button on a single row. The fields render their labels inside the
        // input box so every child shares the same height band and the
        // button sits mid-row, aligned with the inputs.
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            flex: 3,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(line.product.name, style: AppTypography.bodyMedium),
                Text(
                  _weightLabel(line.packetWeight),
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: AppTextField(
              controller: packetController,
              label: AppStrings.RETURN_ORDER_EDIT_PACKETS,
              inlineLabel: true,
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
              validator: _validatePackets,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: AppTextField(
              controller: priceController,
              label: AppStrings.RETURN_ORDER_EDIT_PRICE,
              inlineLabel: true,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              inputFormatters: [_decimalFormatter],
              validator: _validatePrice,
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          // A return with no lines is not editable into existence, so the last
          // line has nothing to remove.
          if (canRemove)
            SecondaryButton(
              label: AppStrings.RETURN_ORDER_EDIT_REMOVE,
              icon: Icons.delete_outline_rounded,
              onPressed: onRemove,
            ),
        ],
      ),
    );
  }

  static final TextInputFormatter _decimalFormatter =
      FilteringTextInputFormatter.allow(RegExp(r'[0-9]*\.?[0-9]*'));

  static String _weightLabel(num weight) {
    final String value = weight == weight.roundToDouble()
        ? weight.toInt().toString()
        : weight.toString();
    return '$value kg packets';
  }

  static String? _validatePackets(String? raw) {
    final int packets = int.tryParse(raw?.trim() ?? '') ?? 0;
    if (packets < 1) return AppStrings.RETURN_ORDER_EDIT_PACKETS_MIN;
    return null;
  }

  static String? _validatePrice(String? raw) {
    final num price = num.tryParse(raw?.trim() ?? '') ?? -1;
    if (price < 0) return AppStrings.RETURN_ORDER_EDIT_PRICE_INVALID;
    return null;
  }
}

class _RemovedLines extends StatelessWidget {
  final List<ReturnOrderItemEditModel> removed;
  final void Function(int index) onRestore;

  const _RemovedLines({required this.removed, required this.onRestore});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          AppStrings.RETURN_ORDER_EDIT_WILL_BE_REMOVED,
          style: AppTypography.labelStrong.copyWith(color: AppColors.ERROR),
        ),
        const SizedBox(height: AppSpacing.xs),
        for (int index = 0; index < removed.length; index++)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.xs),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    removed[index].product.name,
                    style: AppTypography.bodySmall.copyWith(
                      color: AppColors.TEXT_DISABLED,
                    ),
                  ),
                ),
                SecondaryButton(
                  label: AppStrings.RETURN_ORDER_EDIT_RESTORE,
                  onPressed: () => onRestore(index),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _ReadOnlyItemRow extends StatelessWidget {
  final ReturnOrderItemModel item;

  const _ReadOnlyItemRow(this.item);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(item.product.name, style: AppTypography.bodyMedium),
                Text(
                  AppStrings.RETURN_ORDER_ITEM_PACKET_SUMMARY
                      .replaceAll('%s', item.packetWeightLabel)
                      .replaceAll('%t', '${item.packets}'),
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.TEXT_SECONDARY,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                CurrencyFormatter.rupees(item.pricePerPacket),
                style: AppTypography.bodyMedium,
              ),
              Text(
                CurrencyFormatter.rupees(item.lineTotal),
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TotalsRow extends StatelessWidget {
  final int packets;
  final num kg;
  final num amount;

  const _TotalsRow({required this.packets, required this.kg, required this.amount});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_PACKETS,
            value: '$packets',
          ),
        ),
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_KG,
            value: '${_trim(kg)} Kg',
          ),
        ),
        Expanded(
          child: _Total(
            label: AppStrings.COLUMN_RETURN_AMOUNT,
            value: CurrencyFormatter.rupees(amount),
          ),
        ),
      ],
    );
  }

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}

class _Total extends StatelessWidget {
  final String label;
  final String value;

  const _Total({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          label,
          style: AppTypography.bodySmall.copyWith(
            color: AppColors.TEXT_SECONDARY,
          ),
        ),
        Text(value, style: AppTypography.titleMedium),
      ],
    );
  }
}

class _LotList extends StatelessWidget {
  final String label;
  final List<String> lots;

  const _LotList({required this.label, required this.lots});

  @override
  Widget build(BuildContext context) {
    if (lots.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
          Text(lots.join(', '), style: AppTypography.bodyMedium),
        ],
      ),
    );
  }
}
