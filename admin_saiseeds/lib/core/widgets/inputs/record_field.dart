import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../utils/toast_utils.dart';
import 'app_text_field.dart';

class RecordField extends StatelessWidget {
  final TextEditingController controller;
  final String? label;
  final String? hint;
  final bool isEditable;
  final bool isLocked;
  final TextInputType keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final String? Function(String?)? validator;
  final ValueChanged<String>? onChanged;

  const RecordField({
    super.key,
    required this.controller,
    this.label,
    required this.isEditable,
    this.hint,
    this.isLocked = false,
    this.keyboardType = TextInputType.text,
    this.inputFormatters,
    this.validator,
    this.onChanged,
  });

  bool get _isWritable => isEditable && !isLocked;

  void _onBlockedTap(BuildContext context) {
    ToastUtils.showInfo(
      context,
      AppStrings.VIEW_MODE_TOAST_TITLE,
      description: isLocked
          ? AppStrings.VIEW_MODE_LOCKED_TOAST_BODY
          : AppStrings.VIEW_MODE_TOAST_BODY,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppTextField(
      controller: controller,
      label: label,
      hint: _isWritable ? hint : null,
      keyboardType: keyboardType,
      inputFormatters: inputFormatters,
      validator: _isWritable ? validator : null,
      onChanged: _isWritable ? onChanged : null,
      readOnly: !_isWritable,
      isMuted: !_isWritable,
      onTap: _isWritable ? null : () => _onBlockedTap(context),
    );
  }
}
