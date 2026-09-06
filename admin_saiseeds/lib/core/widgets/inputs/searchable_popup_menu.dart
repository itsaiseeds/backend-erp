import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class SearchablePopupMenu<T> extends StatefulWidget {
  final List<T> items;
  final String Function(T item) itemToString;
  final ValueChanged<T> onSelected;
  final bool Function(T item)? isSelected;
  final List<T> Function(String query)? optionsBuilder;
  final Widget child;

  const SearchablePopupMenu({
    super.key,
    required this.items,
    required this.itemToString,
    required this.onSelected,
    required this.child,
    this.isSelected,
    this.optionsBuilder,
  });

  @override
  State<SearchablePopupMenu<T>> createState() => _SearchablePopupMenuState<T>();
}

class _SearchablePopupMenuState<T> extends State<SearchablePopupMenu<T>> {
  final LayerLink _layerLink = LayerLink();
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _suggestionsScrollController = ScrollController();
  late final FocusNode _searchFocusNode;
  OverlayEntry? _overlayEntry;
  bool _isOpen = false;
  int _highlightedIndex = -1;
  List<T> _suggestions = const [];

  @override
  void initState() {
    super.initState();
    _searchFocusNode = FocusNode(onKeyEvent: _handleKeyEvent);
    _searchController.addListener(_onSearchChanged);
  }

  @override
  void dispose() {
    _removeOverlay();
    _searchController.dispose();
    _searchFocusNode.dispose();
    _suggestionsScrollController.dispose();
    super.dispose();
  }

  void _onSearchChanged() {
    _highlightedIndex = -1;
    _overlayEntry?.markNeedsBuild();
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  void _openMenu() {
    if (_isOpen) return;
    _overlayEntry = _createOverlayEntry();
    Overlay.of(context).insert(_overlayEntry!);
    setState(() => _isOpen = true);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _searchFocusNode.requestFocus();
    });
  }

  void _closeMenu() {
    if (!_isOpen) return;
    _removeOverlay();
    _searchController.clear();
    if (!mounted) return;
    setState(() {
      _isOpen = false;
      _highlightedIndex = -1;
    });
  }

  KeyEventResult _handleKeyEvent(FocusNode node, KeyEvent event) {
    if (!_isOpen || event is! KeyDownEvent) return KeyEventResult.ignored;

    if (event.logicalKey == LogicalKeyboardKey.escape) {
      _closeMenu();
      return KeyEventResult.handled;
    }
    if (_suggestions.isEmpty) return KeyEventResult.ignored;

    final bool isDown = event.logicalKey == LogicalKeyboardKey.arrowDown;
    final bool isUp = event.logicalKey == LogicalKeyboardKey.arrowUp;
    if (isDown || isUp) {
      if (isDown) {
        _highlightedIndex = (_highlightedIndex + 1) % _suggestions.length;
      } else if (_highlightedIndex <= 0) {
        _highlightedIndex = _suggestions.length - 1;
      } else {
        _highlightedIndex = _highlightedIndex - 1;
      }
      _overlayEntry?.markNeedsBuild();
      _scrollToHighlighted();
      return KeyEventResult.handled;
    }

    if (event.logicalKey == LogicalKeyboardKey.enter ||
        event.logicalKey == LogicalKeyboardKey.numpadEnter) {
      _select(_suggestions[_highlightedIndex < 0 ? 0 : _highlightedIndex]);
      return KeyEventResult.handled;
    }
    return KeyEventResult.ignored;
  }

  void _scrollToHighlighted() {
    if (!_suggestionsScrollController.hasClients || _highlightedIndex < 0) {
      return;
    }
    _suggestionsScrollController.jumpTo(
      (_highlightedIndex * AppSizes.inputHeight).clamp(
        0.0,
        _suggestionsScrollController.position.maxScrollExtent,
      ),
    );
  }

  void _select(T item) {
    widget.onSelected(item);
    _closeMenu();
  }

  List<T> _filtered() {
    final String rawQuery = _searchController.text.trim();
    final List<T> Function(String query)? builder = widget.optionsBuilder;
    if (builder != null) return builder(rawQuery);

    final String query = rawQuery.toLowerCase();
    if (query.isEmpty) return widget.items;
    return widget.items
        .where(
          (item) => widget.itemToString(item).toLowerCase().contains(query),
        )
        .toList();
  }

  OverlayEntry _createOverlayEntry() {
    final RenderBox renderBox = context.findRenderObject() as RenderBox;
    final Size size = renderBox.size;

    return OverlayEntry(
      builder: (overlayContext) {
        _suggestions = _filtered();
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: _closeMenu,
              ),
            ),
            Positioned(
              width: size.width < AppSizes.tableFilterMenuWidth
                  ? AppSizes.tableFilterMenuWidth
                  : size.width,
              child: CompositedTransformFollower(
                link: _layerLink,
                showWhenUnlinked: false,
                offset: Offset(0, size.height + AppSpacing.xs),
                child: Material(
                  color: AppColors.TRANSPARENT,
                  child: Container(
                    constraints: const BoxConstraints(
                      maxHeight: AppSizes.tableFilterMenuMaxHeight,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.SURFACE,
                      border: Border.all(color: AppColors.BORDER),
                      borderRadius: BorderRadius.circular(AppRadius.md),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(AppSpacing.sm),
                          child: TextField(
                            controller: _searchController,
                            focusNode: _searchFocusNode,
                            style: AppTypography.bodyMedium,
                            decoration: InputDecoration(
                              hintText: AppStrings.SEARCH,
                              hintStyle: AppTypography.bodyMedium.copyWith(
                                color: AppColors.TEXT_DISABLED,
                              ),
                              isDense: true,
                              prefixIcon: const Icon(
                                Icons.search_rounded,
                                size: AppSizes.iconMd,
                                color: AppColors.TEXT_SECONDARY,
                              ),
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: AppSpacing.smd,
                                vertical: AppSpacing.sm,
                              ),
                              border: _menuBorder(AppColors.BORDER),
                              enabledBorder: _menuBorder(AppColors.BORDER),
                              focusedBorder: _menuBorder(
                                AppColors.BORDER_FOCUSED,
                              ),
                            ),
                          ),
                        ),
                        Flexible(
                          child: ListView.builder(
                            controller: _suggestionsScrollController,
                            shrinkWrap: true,
                            padding: EdgeInsets.zero,
                            itemCount: _suggestions.length,
                            itemBuilder: (listContext, index) {
                              final T item = _suggestions[index];
                              return _SuggestionTile(
                                label: widget.itemToString(item),
                                isSelected:
                                    widget.isSelected?.call(item) ?? false,
                                isHighlighted: index == _highlightedIndex,
                                onTap: () => _select(item),
                              );
                            },
                          ),
                        ),
                      ],
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

  OutlineInputBorder _menuBorder(Color color) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppRadius.md),
    borderSide: BorderSide(color: color),
  );

  @override
  Widget build(BuildContext context) {
    return CompositedTransformTarget(
      link: _layerLink,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: _isOpen ? _closeMenu : _openMenu,
          child: widget.child,
        ),
      ),
    );
  }
}

class _SuggestionTile extends StatelessWidget {
  final String label;
  final bool isSelected;
  final bool isHighlighted;
  final VoidCallback onTap;

  const _SuggestionTile({
    required this.label,
    required this.isSelected,
    required this.isHighlighted,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: double.infinity,
          color: isHighlighted ? AppColors.SURFACE_VARIANT : AppColors.SURFACE,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.smd,
            vertical: AppSpacing.smd,
          ),
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.labelMedium.copyWith(
              color: isSelected ? AppColors.PRIMARY : AppColors.TEXT_PRIMARY,
            ),
          ),
        ),
      ),
    );
  }
}
