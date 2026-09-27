import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class _SelectHighlightedIntent extends Intent {
  const _SelectHighlightedIntent();
}

class SearchableField<T> extends StatefulWidget {
  final String label;
  final String hintText;
  final T? value;
  final List<T> items;
  final String Function(T item) itemToString;
  final String Function(T item)? searchText;
  final List<T> Function(String query)? optionsBuilder;
  final bool Function(T a, T b) isSame;
  final ValueChanged<T> onSelected;
  final String? errorText;
  final bool enabled;
  final bool isRequired;
  final String? helperText;
  final String? emptyHint;
  final VoidCallback? onBlockedTap;

  const SearchableField({
    super.key,
    required this.label,
    required this.hintText,
    required this.value,
    required this.items,
    required this.itemToString,
    required this.isSame,
    this.searchText,
    this.optionsBuilder,
    required this.onSelected,
    this.errorText,
    this.enabled = true,
    this.isRequired = false,
    this.helperText,
    this.emptyHint,
    this.onBlockedTap,
  });

  @override
  State<SearchableField<T>> createState() => _SearchableFieldState<T>();
}

class _SearchableFieldState<T> extends State<SearchableField<T>> {
  final LayerLink _layerLink = LayerLink();
  final TextEditingController _controller = TextEditingController();
  final ScrollController _listController = ScrollController();
  late final FocusNode _focusNode;

  OverlayEntry? _overlayEntry;
  bool _isOpen = false;
  bool _isPointerInMenu = false;
  int _highlightedIndex = -1;
  List<T> _suggestions = const [];

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode(onKeyEvent: _handleKeyEvent);
    _focusNode.addListener(_onFocusChanged);
    _syncTextToValue();
  }

  @override
  void didUpdateWidget(covariant SearchableField<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.value != widget.value && !_focusNode.hasFocus) {
      _syncTextToValue();
    }
  }

  @override
  void dispose() {
    _removeOverlay();
    _focusNode.removeListener(_onFocusChanged);
    _focusNode.dispose();
    _controller.dispose();
    _listController.dispose();
    super.dispose();
  }

  void _syncTextToValue() {
    final T? current = widget.value;
    _controller.text = current == null ? '' : widget.itemToString(current);
  }

  bool get _canOpen =>
      widget.enabled &&
      (widget.items.isNotEmpty || widget.optionsBuilder != null);

  void _onFocusChanged() {
    if (_focusNode.hasFocus) {
      _controller.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _controller.text.length,
      );
      _openMenu();
      return;
    }

    if (_isPointerInMenu) return;
    _closeMenu();
    _syncTextToValue();
  }

  void _openMenu() {
    if (_isOpen || !_canOpen) return;
    _highlightedIndex = -1;
    _overlayEntry = _createOverlayEntry();
    Overlay.of(context).insert(_overlayEntry!);
    setState(() => _isOpen = true);
  }

  void _closeMenu() {
    if (!_isOpen) return;
    _removeOverlay();
    setState(() {
      _isOpen = false;
      _highlightedIndex = -1;
    });
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  List<T> _filtered() {
    final String query = _controller.text.trim();
    final List<T> Function(String)? builder = widget.optionsBuilder;
    if (builder != null) return builder(query);

    if (query.isEmpty) return widget.items;
    final String needle = query.toLowerCase();
    return widget.items
        .where((item) => _haystack(item).toLowerCase().contains(needle))
        .toList(growable: false);
  }

  String _haystack(T item) =>
      widget.searchText?.call(item) ?? widget.itemToString(item);

  KeyEventResult _handleKeyEvent(FocusNode node, KeyEvent event) {
    if (event is! KeyDownEvent) return KeyEventResult.ignored;

    if (event.logicalKey == LogicalKeyboardKey.escape) {
      if (!_isOpen) return KeyEventResult.ignored;
      _closeMenu();
      _syncTextToValue();
      return KeyEventResult.handled;
    }

    if (!_isOpen) {
      if (event.logicalKey == LogicalKeyboardKey.arrowDown) {
        _openMenu();
        return KeyEventResult.handled;
      }
      return KeyEventResult.ignored;
    }

    if (_suggestions.isEmpty) return KeyEventResult.ignored;

    final bool isDown = event.logicalKey == LogicalKeyboardKey.arrowDown;
    final bool isUp = event.logicalKey == LogicalKeyboardKey.arrowUp;
    if (isDown || isUp) {
      setState(() {
        _highlightedIndex = isDown
            ? (_highlightedIndex + 1) % _suggestions.length
            : _highlightedIndex <= 0
            ? _suggestions.length - 1
            : _highlightedIndex - 1;
      });
      _overlayEntry?.markNeedsBuild();
      _scrollToHighlighted();
      return KeyEventResult.handled;
    }

    return KeyEventResult.ignored;
  }

  void _scrollToHighlighted() {
    if (!_listController.hasClients || _highlightedIndex < 0) return;
    _listController.animateTo(
      (_highlightedIndex * AppSizes.searchOptionHeight).clamp(
        0.0,
        _listController.position.maxScrollExtent,
      ),
      duration: const Duration(milliseconds: 120),
      curve: Curves.easeOut,
    );
  }

  void _selectItem(T item) {
    _isPointerInMenu = false;
    _controller.text = widget.itemToString(item);
    _controller.selection = TextSelection.fromPosition(
      TextPosition(offset: _controller.text.length),
    );
    widget.onSelected(item);
    _closeMenu();
    _focusNode.unfocus();
  }

  void _selectHighlighted() {
    if (!_isOpen || _suggestions.isEmpty) return;
    final int index = _highlightedIndex < 0 ? 0 : _highlightedIndex;
    if (index >= _suggestions.length) return;
    _selectItem(_suggestions[index]);
  }

  OverlayEntry _createOverlayEntry() {
    final RenderBox box = context.findRenderObject() as RenderBox;
    final Size size = box.size;

    return OverlayEntry(
      builder: (overlayContext) {
        _suggestions = _filtered();

        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: () {
                  _focusNode.unfocus();
                  _closeMenu();
                  _syncTextToValue();
                },
              ),
            ),
            Positioned(
              left: 0,
              top: 0,
              width: size.width,
              child: CompositedTransformFollower(
                link: _layerLink,
                showWhenUnlinked: false,
                offset: Offset(0, size.height + AppSpacing.xs),
                child: Listener(
                  onPointerDown: (_) => _isPointerInMenu = true,
                  onPointerUp: (_) => _isPointerInMenu = false,
                  onPointerCancel: (_) => _isPointerInMenu = false,
                  child: Material(
                    color: AppColors.TRANSPARENT,
                    child: Container(
                      constraints: const BoxConstraints(
                        maxHeight: AppSizes.searchMenuMaxHeight,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.SURFACE,
                        border: Border.all(color: AppColors.BORDER),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                      clipBehavior: Clip.antiAlias,
                      child: _suggestions.isEmpty
                          ? const Padding(
                              padding: EdgeInsets.all(AppSpacing.md),
                              child: Text(AppStrings.NO_RESULTS_FOUND),
                            )
                          : ListView.builder(
                              controller: _listController,
                              padding: EdgeInsets.zero,
                              shrinkWrap: true,
                              itemCount: _suggestions.length,
                              itemBuilder: (context, index) =>
                                  _buildOption(_suggestions[index], index),
                            ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildOption(T item, int index) {
    final T? current = widget.value;
    final bool isSelected = current != null && widget.isSame(item, current);
    final bool isHighlighted = index == _highlightedIndex;

    return Material(
      color: isHighlighted ? AppColors.PRIMARY_SURFACE : AppColors.TRANSPARENT,
      child: InkWell(
        onTap: () => _selectItem(item),
        mouseCursor: SystemMouseCursors.click,
        child: Container(
          height: AppSizes.searchOptionHeight,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          alignment: Alignment.centerLeft,
          child: Row(
            children: [
              Expanded(
                child: Text(
                  widget.itemToString(item),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodyMedium.copyWith(
                    color: isSelected || isHighlighted
                        ? AppColors.PRIMARY
                        : AppColors.TEXT_PRIMARY,
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
                ),
              ),
              if (isSelected)
                const Icon(
                  Icons.check_rounded,
                  size: AppSizes.iconMd,
                  color: AppColors.PRIMARY,
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool hasError =
        widget.errorText != null && widget.errorText!.isNotEmpty;
    final String? helper = widget.helperText;
    final String? emptyHint = widget.emptyHint;
    final bool isEmptySource = widget.items.isEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        RichText(
          text: TextSpan(
            text: widget.label,
            style: AppTypography.labelStrong,
            children: widget.isRequired
                ? [
                    TextSpan(
                      text: AppStrings.REQUIRED_MARKER,
                      style: AppTypography.labelStrong.copyWith(
                        color: AppColors.ERROR,
                      ),
                    ),
                  ]
                : null,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        _BlockedTapCatcher(
          onBlockedTap: _canOpen ? null : widget.onBlockedTap,
          child: CompositedTransformTarget(
          link: _layerLink,
          child: Shortcuts(
            shortcuts: const <ShortcutActivator, Intent>{
              SingleActivator(LogicalKeyboardKey.enter):
                  _SelectHighlightedIntent(),
              SingleActivator(LogicalKeyboardKey.numpadEnter):
                  _SelectHighlightedIntent(),
            },
            child: Actions(
              actions: <Type, Action<Intent>>{
                _SelectHighlightedIntent:
                    CallbackAction<_SelectHighlightedIntent>(
                      onInvoke: (intent) {
                        _selectHighlighted();
                        return null;
                      },
                    ),
              },
              child: TextField(
                controller: _controller,
                focusNode: _focusNode,
                enabled: _canOpen,
                style: AppTypography.bodyMedium,
                cursorColor: AppColors.PRIMARY,
                onChanged: (_) {
                  _highlightedIndex = -1;
                  if (!_isOpen) _openMenu();
                  _overlayEntry?.markNeedsBuild();
                },
                decoration: InputDecoration(
                  hintText: isEmptySource && emptyHint != null
                      ? emptyHint
                      : widget.hintText,
                  hintStyle: AppTypography.bodyMedium.copyWith(
                    color: AppColors.TEXT_DISABLED,
                  ),
                  filled: true,
                  fillColor: _canOpen
                      ? AppColors.SURFACE
                      : AppColors.SURFACE_VARIANT,
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.md,
                    vertical: AppSpacing.smd,
                  ),
                  suffixIcon: Icon(
                    _isOpen
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    size: AppSizes.iconLg,
                    color: AppColors.TEXT_SECONDARY,
                  ),
                  border: _border(hasError ? AppColors.ERROR : null),
                  enabledBorder: _border(hasError ? AppColors.ERROR : null),
                  disabledBorder: _border(null),
                  focusedBorder: _border(
                    hasError ? AppColors.ERROR : AppColors.BORDER_FOCUSED,
                    width: AppSizes.borderMedium,
                  ),
                ),
              ),
            ),
          ),
        ),
        ),
        if (hasError) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            widget.errorText!,
            style: AppTypography.caption.copyWith(color: AppColors.ERROR),
          ),
        ] else if (helper != null && helper.trim().isNotEmpty) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            helper,
            style: AppTypography.caption.copyWith(color: AppColors.WARNING),
          ),
        ],
      ],
    );
  }

  static OutlineInputBorder _border(
    Color? color, {
    double width = AppSizes.borderThin,
  }) {
    return OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadius.md),
      borderSide: BorderSide(color: color ?? AppColors.BORDER, width: width),
    );
  }
}

class _BlockedTapCatcher extends StatelessWidget {
  final VoidCallback? onBlockedTap;
  final Widget child;

  const _BlockedTapCatcher({required this.onBlockedTap, required this.child});

  @override
  Widget build(BuildContext context) {
    if (onBlockedTap == null) return child;

    return Stack(
      children: [
        child,
        Positioned.fill(
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: onBlockedTap,
          ),
        ),
      ],
    );
  }
}
