import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'date_range_field.dart';
import 'searchable_popup_menu.dart';

class FilterValueOption {
  final String value;
  final String label;

  const FilterValueOption({required this.value, required this.label});
}

typedef FilterSearchCallback =
    void Function({
      required String search,
      required String? sortBy,
      required String? sortOrder,
      required Map<String, String> filters,
    });

class AppFilterSearchBar extends StatefulWidget {
  static const String SORT_ASCENDING = 'asc';
  static const String SORT_DESCENDING = 'desc';

  final TextEditingController controller;
  final String hintText;
  final FilterSearchCallback onSearch;
  final List<String> sortByOptions;
  final String? initialSortBy;
  final String? initialSortOrder;
  final List<String> filterByOptions;
  final Map<String, String> initialFilters;
  final String Function(String key) getHumanReadableFilterName;
  final String Function(String key) getHumanReadableSortName;
  final List<FilterValueOption> Function(String key)? filterValueOptions;
  final String Function(String key, String value)? getFilterValueLabel;
  final bool Function(String key)? isDateRangeFilter;
  final String Function(String key)? getFilterDescription;
  final String Function(String key)? getSortDescription;
  final bool showSort;
  final bool showFilters;
  final double minHeight;

  const AppFilterSearchBar({
    super.key,
    required this.controller,
    required this.hintText,
    required this.onSearch,
    required this.getHumanReadableFilterName,
    required this.getHumanReadableSortName,
    this.sortByOptions = const [],
    this.initialSortBy,
    this.initialSortOrder,
    this.filterByOptions = const [],
    this.initialFilters = const {},
    this.filterValueOptions,
    this.getFilterValueLabel,
    this.isDateRangeFilter,
    this.getFilterDescription,
    this.getSortDescription,
    this.showSort = true,
    this.showFilters = true,
    this.minHeight = AppSizes.tableSearchBarHeight,
  });

  @override
  State<AppFilterSearchBar> createState() => _AppFilterSearchBarState();
}

class _AppFilterSearchBarState extends State<AppFilterSearchBar> {
  late final FocusNode _inlineFocusNode;
  late final FocusNode _searchFocusNode;
  late final TextEditingController _inlineEditingController;
  late Map<String, String> _localFilters;
  String? _activeFilterField;

  @override
  void initState() {
    super.initState();
    _inlineFocusNode = FocusNode();
    _searchFocusNode = FocusNode();
    _inlineEditingController = TextEditingController();
    _localFilters = Map<String, String>.from(widget.initialFilters);
    widget.controller.addListener(_onSearchTextChanged);
  }

  @override
  void didUpdateWidget(covariant AppFilterSearchBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialFilters != oldWidget.initialFilters) {
      _localFilters = Map<String, String>.from(widget.initialFilters);
    }
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onSearchTextChanged);
    _inlineFocusNode.dispose();
    _searchFocusNode.dispose();
    _inlineEditingController.dispose();
    super.dispose();
  }

  void _onSearchTextChanged() {
    if (mounted) setState(() {});
  }

  void _applyInlineFilter({bool focusSearchField = false}) {
    final String? fieldKey = _activeFilterField;
    if (fieldKey == null) return;
    final String value = _inlineEditingController.text.trim();

    setState(() {
      _activeFilterField = null;
      if (value.isEmpty) {
        _localFilters.remove(fieldKey);
      } else {
        _localFilters[fieldKey] = value;
      }
    });
    _inlineEditingController.clear();

    if (focusSearchField) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _searchFocusNode.requestFocus();
      });
    }
  }

  void _performSearch() {
    _applyInlineFilter();
    widget.onSearch(
      search: widget.controller.text.trim(),
      sortBy: widget.initialSortBy,
      sortOrder: widget.initialSortOrder,
      filters: Map<String, String>.from(_localFilters),
    );
  }

  void _beginEditingFilter(String fieldKey, {String initialValue = ''}) {
    if (_activeFilterField != null) _applyInlineFilter();
    setState(() {
      _activeFilterField = fieldKey;
      _inlineEditingController.text = initialValue;
      _inlineEditingController.selection = TextSelection.fromPosition(
        TextPosition(offset: initialValue.length),
      );
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _inlineFocusNode.requestFocus();
    });
  }

  String get _currentSortBy =>
      widget.initialSortBy ??
      (widget.sortByOptions.isNotEmpty ? widget.sortByOptions.first : '');

  String get _currentSortOrder =>
      widget.initialSortOrder ?? AppFilterSearchBar.SORT_DESCENDING;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(minHeight: widget.minHeight),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.smd,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          const Icon(
            Icons.search_rounded,
            color: AppColors.TEXT_SECONDARY,
            size: AppSizes.iconLg,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Wrap(
              spacing: AppSpacing.sm,
              runSpacing: AppSpacing.sm,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                if (widget.showFilters) ..._buildFilterChips(),
                if (widget.showFilters && _activeFilterField != null)
                  _buildInlineFilterEditor(),
                if (widget.showFilters) _buildAddFilterButton(),
                _buildSearchField(),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.smd),
          _buildSearchButton(),
          if (widget.showSort && widget.sortByOptions.isNotEmpty) ...[
            const SizedBox(width: AppSpacing.smd),
            const SizedBox(
              height: AppSpacing.xl,
              width: AppSizes.borderThin,
              child: ColoredBox(color: AppColors.DIVIDER),
            ),
            const SizedBox(width: AppSpacing.smd),
            _buildSortControl(),
          ],
        ],
      ),
    );
  }

  List<Widget> _buildFilterChips() {
    return _localFilters.entries.map((entry) {
      return _FilterChip(
        label: widget.getHumanReadableFilterName(entry.key),
        value: widget.getFilterValueLabel == null
            ? entry.value
            : widget.getFilterValueLabel!(entry.key, entry.value),
        onEdit: () {
          final String value = entry.value;
          setState(() => _localFilters.remove(entry.key));
          _beginEditingFilter(entry.key, initialValue: value);
        },
        onRemove: () {
          setState(() => _localFilters.remove(entry.key));
          _performSearch();
        },
      );
    }).toList();
  }

  Widget _buildInlineFilterEditor() {
    return Container(
      height: AppSizes.tableControlHeight,
      padding: const EdgeInsets.only(
        left: AppSpacing.smd,
        right: AppSpacing.xs,
      ),
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        border: Border.all(color: AppColors.PRIMARY),
        borderRadius: BorderRadius.circular(AppRadius.sm),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Tooltip(
            message:
                widget.getFilterDescription?.call(_activeFilterField!) ?? '',
            child: Text(
              widget.getHumanReadableFilterName(_activeFilterField!),
              style: AppTypography.labelSmall.copyWith(
                color: AppColors.TEXT_PRIMARY,
              ),
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            AppStrings.FILTER_OPERATOR_EQUALS,
            style: AppTypography.labelSmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
          const SizedBox(width: AppSpacing.xs),
          ConstrainedBox(
            constraints: const BoxConstraints(
              minWidth: AppSizes.tableFilterValueMinWidth,
              maxWidth: AppSizes.tableFilterValueMaxWidth,
            ),
            child: IntrinsicWidth(child: _buildFilterValueInput()),
          ),
          const SizedBox(width: AppSpacing.xxs),
          _InlineIconButton(
            icon: Icons.close_rounded,
            color: AppColors.TEXT_SECONDARY,
            tooltip: AppStrings.TABLE_DISCARD_FILTER,
            onTap: () {
              setState(() {
                _activeFilterField = null;
                _inlineEditingController.clear();
              });
            },
          ),
        ],
      ),
    );
  }

  List<FilterValueOption> _optionsForActiveFilter() {
    final String? field = _activeFilterField;
    if (field == null || widget.filterValueOptions == null) return const [];
    return widget.filterValueOptions!(field);
  }

  Widget _buildFilterValueInput() {
    final String? field = _activeFilterField;

    if (field != null && (widget.isDateRangeFilter?.call(field) ?? false)) {
      return DateRangeField(
        value: _inlineEditingController.text,
        onChanged: (value) {
          _inlineEditingController.text = value;
          _applyInlineFilter(focusSearchField: true);
        },
      );
    }

    final List<FilterValueOption> options = _optionsForActiveFilter();

    if (options.isEmpty) {
      return TextField(
        controller: _inlineEditingController,
        focusNode: _inlineFocusNode,
        style: AppTypography.labelMedium,
        decoration: InputDecoration(
          border: InputBorder.none,
          enabledBorder: InputBorder.none,
          focusedBorder: InputBorder.none,
          isDense: true,
          contentPadding: EdgeInsets.zero,
          hintText: AppStrings.TABLE_FILTER_VALUE_HINT,
          hintStyle: AppTypography.labelMedium.copyWith(
            color: AppColors.TEXT_DISABLED,
          ),
          filled: false,
        ),
        onSubmitted: (_) => _performSearch(),
      );
    }

    final String current = _inlineEditingController.text;
    final FilterValueOption? selected = _selectedOption(options, current);

    return SearchablePopupMenu<FilterValueOption>(
      items: options,
      itemToString: (option) => option.label,
      isSelected: (option) => option.value == current,
      onSelected: (option) {
        _inlineEditingController.text = option.value;
        _applyInlineFilter(focusSearchField: true);
      },
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(
              selected?.label ?? AppStrings.TABLE_FILTER_VALUE_HINT,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: AppTypography.labelMedium.copyWith(
                color: selected == null
                    ? AppColors.TEXT_DISABLED
                    : AppColors.TEXT_PRIMARY,
              ),
            ),
          ),
          const Icon(
            Icons.arrow_drop_down_rounded,
            size: AppSizes.iconMd,
            color: AppColors.TEXT_SECONDARY,
          ),
        ],
      ),
    );
  }

  static FilterValueOption? _selectedOption(
    List<FilterValueOption> options,
    String value,
  ) {
    for (final option in options) {
      if (option.value == value) return option;
    }
    return null;
  }

  Widget _buildAddFilterButton() {
    if (widget.filterByOptions.isEmpty) return const SizedBox.shrink();

    return SearchablePopupMenu<String>(
      items: widget.filterByOptions,
      itemToString: widget.getHumanReadableFilterName,
      itemDescription: widget.getFilterDescription,
      isSelected: _localFilters.containsKey,
      onSelected: _beginEditingFilter,
      child: Container(
        height: AppSizes.tableControlHeight,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
        decoration: BoxDecoration(
          border: Border.all(color: AppColors.PRIMARY_LIGHT),
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.add_rounded,
              size: AppSizes.iconSm,
              color: AppColors.PRIMARY,
            ),
            const SizedBox(width: AppSpacing.xs),
            Flexible(
              child: Text(
                AppStrings.TABLE_ADD_FILTER,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelMedium.copyWith(
                  color: AppColors.PRIMARY,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSearchField() {
    return SizedBox(
      height: AppSizes.tableControlHeight,
      child: ConstrainedBox(
        constraints: const BoxConstraints(
          minWidth: AppSizes.tableSearchFieldMinWidth,
        ),
        child: IntrinsicWidth(
          child: TextField(
            controller: widget.controller,
            focusNode: _searchFocusNode,
            textAlignVertical: TextAlignVertical.center,
            style: AppTypography.bodyMedium,
            onSubmitted: (_) => _performSearch(),
            decoration: InputDecoration(
              hintText: _localFilters.isEmpty
                  ? widget.hintText
                  : AppStrings.TABLE_SEARCH_WITHIN_RESULTS,
              hintStyle: AppTypography.bodyMedium.copyWith(
                color: AppColors.TEXT_DISABLED,
              ),
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              isDense: true,
              filled: false,
              contentPadding: const EdgeInsets.symmetric(
                vertical: AppSpacing.sm,
              ),
              suffixIcon: widget.controller.text.isEmpty
                  ? null
                  : _InlineIconButton(
                      icon: Icons.close_rounded,
                      color: AppColors.TEXT_SECONDARY,
                      tooltip: AppStrings.TABLE_CLEAR_SEARCH,
                      onTap: () {
                        widget.controller.clear();
                        _performSearch();
                      },
                    ),
              suffixIconConstraints: const BoxConstraints(
                minWidth: AppSizes.iconXl,
                minHeight: AppSizes.iconXl,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSearchButton() {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: _performSearch,
        child: Container(
          height: AppSizes.tableControlHeight,
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          decoration: BoxDecoration(
            color: AppColors.PRIMARY,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Text(
            AppStrings.TABLE_SEARCH,
            style: AppTypography.labelMedium.copyWith(
              color: AppColors.TEXT_ON_PRIMARY,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSortControl() {
    final bool isAscending =
        _currentSortOrder == AppFilterSearchBar.SORT_ASCENDING;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SearchablePopupMenu<String>(
          items: widget.sortByOptions,
          itemToString: widget.getHumanReadableSortName,
          isSelected: (option) => option == _currentSortBy,
          onSelected: (value) => widget.onSearch(
            search: widget.controller.text.trim(),
            sortBy: value,
            sortOrder: _currentSortOrder,
            filters: Map<String, String>.from(_localFilters),
          ),
          child: Container(
            height: AppSizes.tableControlHeight,
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
            decoration: const BoxDecoration(
              color: AppColors.SURFACE_VARIANT,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(AppRadius.md),
                bottomLeft: Radius.circular(AppRadius.md),
              ),
              border: Border.fromBorderSide(
                BorderSide(color: AppColors.BORDER),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  widget.getHumanReadableSortName(_currentSortBy),
                  style: AppTypography.labelMedium,
                ),
                const SizedBox(width: AppSpacing.xs),
                const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: AppSizes.iconSm,
                  color: AppColors.TEXT_SECONDARY,
                ),
              ],
            ),
          ),
        ),
        MouseRegion(
          cursor: SystemMouseCursors.click,
          child: Tooltip(
            message: AppStrings.TABLE_TOGGLE_SORT_ORDER,
            child: GestureDetector(
              onTap: () => widget.onSearch(
                search: widget.controller.text.trim(),
                sortBy: _currentSortBy,
                sortOrder: isAscending
                    ? AppFilterSearchBar.SORT_DESCENDING
                    : AppFilterSearchBar.SORT_ASCENDING,
                filters: Map<String, String>.from(_localFilters),
              ),
              child: Container(
                height: AppSizes.tableControlHeight,
                width: AppSizes.tableSortOrderWidth,
                alignment: Alignment.center,
                decoration: const BoxDecoration(
                  color: AppColors.SURFACE_VARIANT,
                  borderRadius: BorderRadius.only(
                    topRight: Radius.circular(AppRadius.md),
                    bottomRight: Radius.circular(AppRadius.md),
                  ),
                  border: Border(
                    top: BorderSide(color: AppColors.BORDER),
                    bottom: BorderSide(color: AppColors.BORDER),
                    right: BorderSide(color: AppColors.BORDER),
                  ),
                ),
                child: Icon(
                  isAscending
                      ? Icons.arrow_upward_rounded
                      : Icons.arrow_downward_rounded,
                  size: AppSizes.iconSm,
                  color: AppColors.PRIMARY,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _FilterChip extends StatelessWidget {
  final String label;
  final String value;
  final VoidCallback onEdit;
  final VoidCallback onRemove;

  const _FilterChip({
    required this.label,
    required this.value,
    required this.onEdit,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onEdit,
        child: Container(
          height: AppSizes.tableControlHeight,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
          decoration: BoxDecoration(
            color: AppColors.PRIMARY_SURFACE,
            border: Border.all(color: AppColors.PRIMARY_LIGHT),
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: AppTypography.labelSmall),
              const SizedBox(width: AppSpacing.xs),
              ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: AppSizes.tableFilterValueMaxWidth,
                ),
                child: Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.labelMedium.copyWith(
                    color: AppColors.PRIMARY,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.xs),
              _InlineIconButton(
                icon: Icons.close_rounded,
                color: AppColors.PRIMARY,
                tooltip: AppStrings.TABLE_REMOVE_FILTER,
                onTap: onRemove,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _InlineIconButton extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String tooltip;
  final VoidCallback onTap;

  const _InlineIconButton({
    required this.icon,
    required this.color,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: Tooltip(
        message: tooltip,
        child: GestureDetector(
          onTap: onTap,
          child: Icon(icon, size: AppSizes.iconSm, color: color),
        ),
      ),
    );
  }
}
