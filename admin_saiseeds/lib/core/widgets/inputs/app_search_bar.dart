import 'dart:async';
import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppSearchBar extends StatefulWidget {
  final TextEditingController? controller;
  final String? hint;
  final ValueChanged<String> onChanged;
  final Duration debounceDuration;

  const AppSearchBar({
    super.key,
    this.controller,
    this.hint,
    required this.onChanged,
    this.debounceDuration = const Duration(milliseconds: 400),
  });

  @override
  State<AppSearchBar> createState() => _AppSearchBarState();
}

class _AppSearchBarState extends State<AppSearchBar> {
  late final TextEditingController _controller;
  late final bool _ownsController;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ?? TextEditingController();
    _controller.addListener(_handleTextChanged);
  }

  void _handleTextChanged() {
    setState(() {});
    _debounce?.cancel();
    _debounce = Timer(
      widget.debounceDuration,
      () => widget.onChanged(_controller.text),
    );
  }

  void _clear() {
    _controller.clear();
    _debounce?.cancel();
    widget.onChanged('');
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.removeListener(_handleTextChanged);
    if (_ownsController) _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
      child: Row(
        children: [
          const Icon(
            Icons.search_rounded,
            size: AppSpacing.md,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: TextField(
              controller: _controller,
              style: AppTypography.bodyMedium,
              textAlignVertical: TextAlignVertical.center,
              decoration: InputDecoration(
                hintText: widget.hint ?? AppStrings.SEARCH,
                hintStyle: AppTypography.bodyMedium.copyWith(
                  color: AppColors.TEXT_DISABLED,
                ),
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(
                  vertical: AppSpacing.sm,
                ),
              ),
            ),
          ),
          if (_controller.text.isNotEmpty)
            MouseRegion(
              cursor: SystemMouseCursors.click,
              child: IconButton(
                icon: const Icon(
                  Icons.close_rounded,
                  size: AppSpacing.md,
                  color: AppColors.TEXT_SECONDARY,
                ),
                onPressed: _clear,
              ),
            ),
        ],
      ),
    );
  }
}
