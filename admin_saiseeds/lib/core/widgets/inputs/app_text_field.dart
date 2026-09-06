import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppTextField extends StatefulWidget {
  final TextEditingController? controller;
  final String? label;
  final String? hint;
  final String? errorText;
  final String? Function(String?)? validator;
  final bool obscureText;
  final IconData? prefixIcon;
  final Widget? suffixIcon;
  final TextInputType keyboardType;
  final List<TextInputFormatter>? inputFormatters;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final bool enabled;
  final bool readOnly;
  final VoidCallback? onTap;
  final int maxLines;
  final FocusNode? focusNode;
  final String? prefixText;
  final TextStyle? labelStyle;

  const AppTextField({
    super.key,
    this.controller,
    this.label,
    this.hint,
    this.errorText,
    this.validator,
    this.obscureText = false,
    this.prefixIcon,
    this.suffixIcon,
    this.keyboardType = TextInputType.text,
    this.inputFormatters,
    this.onChanged,
    this.onSubmitted,
    this.enabled = true,
    this.readOnly = false,
    this.onTap,
    this.maxLines = 1,
    this.focusNode,
    this.prefixText,
    this.labelStyle,
  });

  @override
  State<AppTextField> createState() => _AppTextFieldState();
}

class _AppTextFieldState extends State<AppTextField> {
  bool _obscure = true;

  @override
  void initState() {
    super.initState();
    _obscure = widget.obscureText;
  }

  OutlineInputBorder _border(Color color, {double width = 1}) =>
      OutlineInputBorder(
        borderRadius: BorderRadius.circular(AppRadius.md),
        borderSide: BorderSide(color: color, width: width),
      );

  Widget? _buildPrefix() {
    if (widget.prefixText != null) {
      return _AppTextFieldPrefix(
        text: widget.prefixText!,
        enabled: widget.enabled,
      );
    }
    if (widget.prefixIcon != null) {
      return Icon(
        widget.prefixIcon,
        size: AppSizes.iconSm,
        color: AppColors.TEXT_SECONDARY,
      );
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.label != null) ...[
          Text(widget.label!, style: widget.labelStyle ?? AppTypography.label),
          const SizedBox(height: AppSpacing.sm),
        ],
        TextFormField(
          controller: widget.controller,
          focusNode: widget.focusNode,
          obscureText: widget.obscureText && _obscure,
          keyboardType: widget.keyboardType,
          inputFormatters: widget.inputFormatters,
          validator: widget.validator,
          onChanged: widget.onChanged,
          onFieldSubmitted: widget.onSubmitted,
          enabled: widget.enabled,
          readOnly: widget.readOnly,
          onTap: widget.onTap,
          maxLines: widget.obscureText ? 1 : widget.maxLines,
          style: AppTypography.bodyMedium,
          decoration: InputDecoration(
            hintText: widget.hint,
            errorText: widget.errorText,
            hintStyle: AppTypography.bodyMedium.copyWith(
              color: AppColors.TEXT_DISABLED,
            ),
            filled: true,
            fillColor: widget.enabled
                ? AppColors.SURFACE
                : AppColors.SURFACE_VARIANT,
            contentPadding: EdgeInsets.only(
              left: widget.prefixText != null ? AppSpacing.smd : AppSpacing.md,
              right: AppSpacing.md,
              top: AppSpacing.smd,
              bottom: AppSpacing.smd,
            ),
            prefixIcon: _buildPrefix(),
            prefixIconConstraints: widget.prefixText != null
                ? const BoxConstraints(
                    minWidth: AppSizes.phonePrefixWidth,
                    minHeight: AppSizes.inputHeight,
                  )
                : null,
            suffixIcon: widget.obscureText
                ? MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: IconButton(
                      icon: Icon(
                        _obscure
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        size: AppSizes.iconSm,
                        color: AppColors.TEXT_SECONDARY,
                      ),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                  )
                : widget.suffixIcon,
            border: _border(AppColors.BORDER),
            enabledBorder: _border(AppColors.BORDER),
            focusedBorder: _border(
              AppColors.BORDER_FOCUSED,
              width: AppSizes.borderThick,
            ),
            disabledBorder: _border(AppColors.BORDER),
            errorBorder: _border(AppColors.ERROR),
            focusedErrorBorder: _border(
              AppColors.ERROR,
              width: AppSizes.borderMedium,
            ),
          ),
        ),
      ],
    );
  }
}

class _AppTextFieldPrefix extends StatelessWidget {
  final String text;
  final bool enabled;

  const _AppTextFieldPrefix({required this.text, required this.enabled});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
          child: Text(
            text,
            style: AppTypography.bodyMedium.copyWith(
              fontWeight: FontWeight.w600,
              color: enabled
                  ? AppColors.TEXT_SECONDARY
                  : AppColors.TEXT_DISABLED,
            ),
          ),
        ),
        Container(
          width: AppSizes.borderThin,
          height: AppSpacing.md,
          color: AppColors.DIVIDER,
        ),
        const SizedBox(width: AppSpacing.smd),
      ],
    );
  }
}
