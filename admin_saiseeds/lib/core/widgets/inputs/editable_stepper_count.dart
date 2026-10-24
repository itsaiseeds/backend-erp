import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// The number between a stepper's -/+ buttons, tappable to type a value
/// directly instead of stepping one at a time -- a 300-bag order should not
/// need 300 taps. Visually just the number: callers keep their own
/// surrounding container, sizing and colors, this only swaps the static
/// `Text` for an inline `TextField` that looks identical until focused.
class EditableStepperCount extends StatefulWidget {
  final int value;
  final TextStyle style;
  final double minWidth;
  final bool enabled;
  final int maxDigits;

  /// Fires once the typed value is committed (on submit or on losing focus).
  /// Not called for keystrokes in between -- callers that want to validate
  /// a max (e.g. against available stock) do it here and clamp/reject.
  final ValueChanged<int> onSubmitted;

  const EditableStepperCount({
    super.key,
    required this.value,
    required this.style,
    required this.onSubmitted,
    this.minWidth = 28,
    this.enabled = true,
    this.maxDigits = 6,
  });

  @override
  State<EditableStepperCount> createState() => _EditableStepperCountState();
}

class _EditableStepperCountState extends State<EditableStepperCount> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: '${widget.value}');
    _focusNode = FocusNode()..addListener(_onFocusChanged);
  }

  @override
  void didUpdateWidget(EditableStepperCount oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value == oldWidget.value) return;
    if (_focusNode.hasFocus) return;
    _controller.text = '${widget.value}';
  }

  @override
  void dispose() {
    _focusNode.removeListener(_onFocusChanged);
    _focusNode.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _onFocusChanged() {
    if (!_focusNode.hasFocus) _commit();
  }

  void _commit() {
    final int? parsed = int.tryParse(_controller.text.trim());
    if (parsed == null || parsed < 1) {
      _controller.text = '${widget.value}';
      return;
    }
    if (parsed != widget.value) widget.onSubmitted(parsed);
    _controller.text = '$parsed';
  }

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: BoxConstraints(minWidth: widget.minWidth),
      child: IntrinsicWidth(
        child: TextField(
          controller: _controller,
          focusNode: _focusNode,
          enabled: widget.enabled,
          textAlign: TextAlign.center,
          keyboardType: TextInputType.number,
          cursorColor: widget.style.color,
          style: widget.style,
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(widget.maxDigits),
          ],
          onSubmitted: (_) => _focusNode.unfocus(),
          onTapOutside: (_) => _focusNode.unfocus(),
          decoration: const InputDecoration(
            isDense: true,
            isCollapsed: true,
            contentPadding: EdgeInsets.zero,
            filled: false,
            fillColor: Colors.transparent,
            border: InputBorder.none,
            enabledBorder: InputBorder.none,
            focusedBorder: InputBorder.none,
            disabledBorder: InputBorder.none,
          ),
          cursorHeight: (widget.style.fontSize ?? 14) + 2,
        ),
      ),
    );
  }
}
