import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class OtpInputField extends StatefulWidget {
  final int length;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onCompleted;
  final String? errorText;
  final bool enabled;
  final bool showGroupSeparator;

  const OtpInputField({
    super.key,
    this.length = 6,
    this.onChanged,
    this.onCompleted,
    this.errorText,
    this.enabled = true,
    this.showGroupSeparator = true,
  });

  @override
  State<OtpInputField> createState() => _OtpInputFieldState();
}

class _OtpInputFieldState extends State<OtpInputField> {
  late final List<TextEditingController> _controllers;
  late final List<FocusNode> _focusNodes;

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(widget.length, (_) => TextEditingController());
    _focusNodes = List.generate(widget.length, (_) => FocusNode());
    for (final node in _focusNodes) {
      node.addListener(_onFocusChanged);
    }
  }

  @override
  void dispose() {
    for (final controller in _controllers) {
      controller.dispose();
    }
    for (final node in _focusNodes) {
      node.removeListener(_onFocusChanged);
      node.dispose();
    }
    super.dispose();
  }

  void _onFocusChanged() {
    if (mounted) setState(() {});
  }

  String get _code => _controllers.map((c) => c.text).join();

  void _notify() {
    final code = _code;
    widget.onChanged?.call(code);
    if (code.length == widget.length) {
      widget.onCompleted?.call(code);
    }
  }

  void _distribute(String digits, int startIndex) {
    var cursor = startIndex;
    for (final digit in digits.split('')) {
      if (cursor >= widget.length) break;
      _controllers[cursor].text = digit;
      cursor++;
    }
    final nextIndex = cursor.clamp(0, widget.length - 1);
    if (cursor >= widget.length) {
      _focusNodes[widget.length - 1].unfocus();
    } else {
      _focusNodes[nextIndex].requestFocus();
    }
    setState(() {});
    _notify();
  }

  void _onDigitChanged(String value, int index) {
    final digits = value.replaceAll(RegExp(r'\D'), '');

    if (digits.length > 1) {
      _distribute(digits, index);
      return;
    }

    _controllers[index].text = digits;
    _controllers[index].selection = TextSelection.collapsed(
      offset: digits.length,
    );

    if (digits.isNotEmpty && index < widget.length - 1) {
      _focusNodes[index + 1].requestFocus();
    } else if (digits.isNotEmpty) {
      _focusNodes[index].unfocus();
    }

    setState(() {});
    _notify();
  }

  KeyEventResult _onKeyEvent(KeyEvent event, int index) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;
    if (event.logicalKey != LogicalKeyboardKey.backspace) {
      return KeyEventResult.ignored;
    }
    if (_controllers[index].text.isNotEmpty || index == 0) {
      return KeyEventResult.ignored;
    }
    _controllers[index - 1].clear();
    _focusNodes[index - 1].requestFocus();
    setState(() {});
    _notify();
    return KeyEventResult.handled;
  }

  bool _isFilled(int index) => _controllers[index].text.isNotEmpty;

  bool get _hasError => widget.errorText != null;

  Color _borderColorFor(int index) {
    if (_hasError) return AppColors.ERROR;
    if (!widget.enabled) return AppColors.BORDER;
    if (_focusNodes[index].hasFocus) return AppColors.PRIMARY;
    if (_isFilled(index)) return AppColors.BORDER_STRONG;
    return AppColors.BORDER;
  }

  double _borderWidthFor(int index) {
    if (_focusNodes[index].hasFocus) return AppSizes.borderThick;
    if (_hasError) return AppSizes.borderMedium;
    return AppSizes.borderThin;
  }

  Color _fillColorFor(int index) {
    if (!widget.enabled) return AppColors.SURFACE_VARIANT;
    if (_focusNodes[index].hasFocus) return AppColors.PRIMARY_SURFACE;
    if (_hasError) return AppColors.ERROR_LIGHT;
    return AppColors.SURFACE;
  }

  Color _digitColorFor(int index) {
    if (!widget.enabled) return AppColors.TEXT_DISABLED;
    if (_hasError) return AppColors.ERROR;
    return AppColors.TEXT_PRIMARY;
  }

  bool _hasSeparatorAfter(int index) {
    if (!widget.showGroupSeparator) return false;
    if (widget.length < 4 || widget.length.isOdd) return false;
    return index == (widget.length ~/ 2) - 1;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            for (int index = 0; index < widget.length; index++) ...[
              Expanded(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(
                    maxWidth: AppSizes.otpBoxMaxWidth,
                  ),
                  child: _buildBox(index),
                ),
              ),
              if (index != widget.length - 1)
                _hasSeparatorAfter(index)
                    ? const _OtpGroupSeparator()
                    : const SizedBox(width: AppSpacing.sm),
            ],
          ],
        ),
        if (widget.errorText != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            widget.errorText!,
            style: AppTypography.caption.copyWith(
              color: AppColors.ERROR,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildBox(int index) {
    return SizedBox(
      height: AppSizes.otpBoxHeight,
      child: Focus(
        onKeyEvent: (node, event) => _onKeyEvent(event, index),
        child: TextField(
          controller: _controllers[index],
          focusNode: _focusNodes[index],
          enabled: widget.enabled,
          textAlign: TextAlign.center,
          textAlignVertical: TextAlignVertical.center,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          showCursor: false,
          style: AppTypography.otpDigit.copyWith(color: _digitColorFor(index)),
          decoration: InputDecoration(
            counterText: '',
            filled: true,
            fillColor: _fillColorFor(index),
            contentPadding: EdgeInsets.zero,
            border: _boxBorder(index),
            enabledBorder: _boxBorder(index),
            focusedBorder: _boxBorder(index),
            disabledBorder: _boxBorder(index),
            errorBorder: _boxBorder(index),
            focusedErrorBorder: _boxBorder(index),
          ),
          onChanged: (value) => _onDigitChanged(value, index),
        ),
      ),
    );
  }

  OutlineInputBorder _boxBorder(int index) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppRadius.md),
    borderSide: BorderSide(
      color: _borderColorFor(index),
      width: _borderWidthFor(index),
    ),
  );
}

class _OtpGroupSeparator extends StatelessWidget {
  const _OtpGroupSeparator();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: AppSizes.otpGroupSeparator * 2,
      alignment: Alignment.center,
      child: Container(
        width: AppSizes.otpSeparatorWidth,
        height: AppSizes.borderThick,
        decoration: const BoxDecoration(
          color: AppColors.BORDER_STRONG,
          borderRadius: BorderRadius.all(Radius.circular(AppRadius.full)),
        ),
      ),
    );
  }
}
