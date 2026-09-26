import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class StockCountField extends StatefulWidget {
  static const int MAX_DIGITS = 9;

  final int? value;
  final bool enabled;
  final ValueChanged<int?> onChanged;

  const StockCountField({
    super.key,
    required this.value,
    required this.onChanged,
    this.enabled = true,
  });

  @override
  State<StockCountField> createState() => _StockCountFieldState();
}

class _StockCountFieldState extends State<StockCountField> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _isFocused = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: _textOf(widget.value));
    _focusNode = FocusNode()..addListener(_onFocusChanged);
  }

  @override
  void didUpdateWidget(StockCountField oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value == oldWidget.value) return;

    final String next = _textOf(widget.value);
    if (_controller.text == next) return;
    _controller.text = next;
  }

  @override
  void dispose() {
    _focusNode.removeListener(_onFocusChanged);
    _focusNode.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _onFocusChanged() => setState(() => _isFocused = _focusNode.hasFocus);

  void _onChanged(String raw) {
    final String trimmed = raw.trim();
    widget.onChanged(trimmed.isEmpty ? null : int.tryParse(trimmed));
  }

  static String _textOf(int? value) => value == null ? '' : '$value';

  @override
  Widget build(BuildContext context) {
    final bool hasValue = widget.value != null;

    final Color fill = !widget.enabled
        ? AppColors.SURFACE_VARIANT
        : _isFocused
        ? AppColors.PRIMARY_SURFACE
        : hasValue
        ? AppColors.SUCCESS_LIGHT
        : AppColors.TRANSPARENT;

    return SizedBox(
      height: double.infinity,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
        child: Material(
          color: fill,
          borderRadius: BorderRadius.circular(AppRadius.sm),
          child: TextField(
            controller: _controller,
            focusNode: _focusNode,
            enabled: widget.enabled,
            keyboardType: TextInputType.number,
            textAlign: TextAlign.center,
            textAlignVertical: TextAlignVertical.center,
            expands: true,
            maxLines: null,
            minLines: null,
            cursorColor: AppColors.PRIMARY,
            style: AppTypography.tableCellStrong.copyWith(
              color: hasValue ? AppColors.PRIMARY_DARK : AppColors.TEXT_PRIMARY,
            ),
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(StockCountField.MAX_DIGITS),
            ],
            onChanged: _onChanged,
            decoration: InputDecoration(
              isDense: true,
              hintText: AppStrings.STOCK_COUNT_HINT,
              hintStyle: AppTypography.tableCell.copyWith(
                color: AppColors.TEXT_DISABLED,
              ),
              hintMaxLines: 1,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: AppSpacing.xs,
              ),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              disabledBorder: InputBorder.none,
            ),
          ),
        ),
      ),
    );
  }
}
