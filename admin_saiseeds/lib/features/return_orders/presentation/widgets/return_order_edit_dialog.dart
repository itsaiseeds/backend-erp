import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/return_order_edit_model.dart';
import '../../data/models/return_order_model.dart';
import '../../data/return_orders_repository.dart';

/// Editing a pending return.
///
/// The API replaces the whole return on every save, so this editor is
/// deliberately not a diff editor: it holds the complete set of lines, shows
/// what is about to be deleted, and sends all of it. Editing product, packet
/// weight or line identity is not offered because those come from the challan --
/// changing them here would let the return describe stock the order never had.
class ReturnOrderEditDialog extends StatefulWidget {
  final ReturnOrderModel returnOrder;
  final ReturnOrdersRepository repository;

  const ReturnOrderEditDialog({
    super.key,
    required this.returnOrder,
    required this.repository,
  });

  static Future<bool> show(
    BuildContext context, {
    required ReturnOrderModel returnOrder,
    required ReturnOrdersRepository repository,
  }) async {
    final bool? saved = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => ReturnOrderEditDialog(
        returnOrder: returnOrder,
        repository: repository,
      ),
    );
    return saved ?? false;
  }

  @override
  State<ReturnOrderEditDialog> createState() => _ReturnOrderEditDialogState();
}

class _ReturnOrderEditDialogState extends State<ReturnOrderEditDialog> {
  late DateTime? _returnDate;

  /// Kept in sync with [_controllers] by index; see [_removeLine].
  late final List<ReturnOrderItemEditModel> _lines;

  late final List<TextEditingController> _packetControllers;
  late final List<TextEditingController> _priceControllers;

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();

  bool _isSubmitting = false;
  String? _error;

  /// Lines the admin has removed but not yet saved. Held apart from the live
  /// list so the footer can say what saving will cost before it happens.
  final List<ReturnOrderItemEditModel> _removed = [];

  @override
  void initState() {
    super.initState();
    _returnDate = widget.returnOrder.returnDate;
    _lines = widget.returnOrder.items
        .map(ReturnOrderItemEditModel.fromItem)
        .toList(growable: true);
    _packetControllers = _lines.map(_packetController).toList();
    _priceControllers = _lines.map(_priceController).toList();
  }

  @override
  void dispose() {
    for (final controller in _packetControllers) {
      controller.dispose();
    }
    for (final controller in _priceControllers) {
      controller.dispose();
    }
    super.dispose();
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

  num get _liveKg => _lines.fold<num>(0, (sum, line) => sum + line.kg);

  num get _liveTotal =>
      _lines.fold<num>(0, (sum, line) => sum + line.lineTotal);

  int get _livePackets {
    int total = 0;
    for (final controller in _packetControllers) {
      total += int.tryParse(controller.text.trim()) ?? 0;
    }
    return total;
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

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    final List<ReturnOrderItemEditModel> items = [
      for (int index = 0; index < _lines.length; index++)
        _lines[index].copyWith(
          packets: int.parse(_packetControllers[index].text.trim()),
          pricePerPacket: num.parse(_priceControllers[index].text.trim()),
        ),
    ];

    setState(() {
      _isSubmitting = true;
      _error = null;
    });

    try {
      await widget.repository.updateReturn(
        publicId: widget.returnOrder.publicId,
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
      icon: Icons.edit_note_rounded,
      title: AppStrings.RETURN_ORDER_EDIT_TITLE,
      subtitle: widget.returnOrder.publicId,
      mode: RecordDialogMode.edit,
      isTall: true,
      isSubmitting: _isSubmitting,
      submitLabel: AppStrings.RETURN_ORDER_EDIT_SAVE,
      onSubmit: _isSubmitting ? null : _submit,
      body: Form(
        key: _formKey,
        child: Column(
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
            SectionTitle(
              title: _linesLabel,
              icon: Icons.inventory_2_outlined,
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.md),
            if (_lines.isEmpty)
              Text(
                AppStrings.RETURN_ORDER_EDIT_EMPTY,
                style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
              )
            else
              for (int index = 0; index < _lines.length; index++)
                _LineEditor(
                  key: ValueKey('${_lines[index].product.publicId}#index'),
                  line: _lines[index],
                  packetController: _packetControllers[index],
                  priceController: _priceControllers[index],
                  canRemove: _lines.length > 1,
                  onRemove: () => _removeLine(index),
                ),
            if (_removed.isNotEmpty) ...[
              const SizedBox(height: AppSpacing.sm),
              _RemovedLines(removed: _removed, onRestore: _restoreLine),
            ],
            const SizedBox(height: AppSpacing.md),
            const AppHairline(),
            const SizedBox(height: AppSpacing.md),
            _LiveTotals(packets: _livePackets, kg: _liveKg, amount: _liveTotal),
            if (_error != null) ...[
              const SizedBox(height: AppSpacing.md),
              Text(
                _error!,
                style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String get _linesLabel {
    final int count = _lines.length;
    return count == 1
        ? '1 ${AppStrings.RETURN_ORDER_ITEM_COUNT_ONE}'
        : '$count ${AppStrings.RETURN_ORDER_ITEM_COUNT_MANY}';
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
        crossAxisAlignment: CrossAxisAlignment.start,
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

class _LiveTotals extends StatelessWidget {
  final int packets;
  final num kg;
  final num amount;

  const _LiveTotals({
    required this.packets,
    required this.kg,
    required this.amount,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _Total(label: AppStrings.COLUMN_RETURN_PACKETS, value: '$packets'),
        _Total(label: AppStrings.COLUMN_RETURN_KG, value: '${_trim(kg)} Kg'),
        _Total(
          label: AppStrings.COLUMN_RETURN_AMOUNT,
          value: CurrencyFormatter.rupees(amount),
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
    return Expanded(
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
          Text(value, style: AppTypography.titleMedium),
        ],
      ),
    );
  }
}
