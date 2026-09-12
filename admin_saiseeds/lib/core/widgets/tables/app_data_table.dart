import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../services/storage_service.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/app_scroll_behavior.dart';
import '../../utils/toast_utils.dart';
import '../feedback/empty_state.dart';
import '../inputs/app_filter_search_bar.dart';
import '../loaders/shimmer_rows.dart';
import 'app_data_column.dart';
import 'app_pagination.dart';
import 'bulk_action_buttons.dart';
import 'column_resize_handle.dart';
import 'column_settings_dialog.dart';
import 'responsive_table_layout.dart';

typedef TableFetchCallback =
    void Function({
      required int page,
      required int limit,
      String? search,
      String? sortBy,
      String? sortOrder,
      Map<String, String>? filters,
    });

typedef TableCellBuilder<T> =
    Widget Function(BuildContext context, T item, AppDataColumn column);

typedef BulkActionsBuilder =
    Widget Function(
      BuildContext context,
      Map<String, String> selection,
      VoidCallback onCompleted,
    );

class AppDataTable<T> extends StatefulWidget {
  static const double standardRowHeight = AppSizes.tableCompactRowHeight;
  static const String SELECT_COLUMN_ID = AppStrings.TABLE_SELECT_COLUMN_LABEL;
  static const String CONFIG_PINNED_KEY = 'pinned';
  static const String CONFIG_HIDDEN_KEY = 'hidden';

  final List<T> items;
  final bool isLoading;
  final bool isOperationInProgress;
  final int currentPage;
  final int totalPages;
  final int totalItems;

  final TableFetchCallback? onFetchData;

  final List<String> sortByOptions;
  final List<String> filterByOptions;
  final String? currentSortBy;
  final String? currentSortOrder;
  final Map<String, String> currentFilters;
  final String Function(String filter)? getHumanReadableFilterName;
  final List<FilterValueOption> Function(String filter)? filterValueOptions;
  final String Function(String filter, String value)? getFilterValueLabel;
  final bool Function(String filter)? isDateRangeFilter;
  final String Function(String filter)? getFilterDescription;
  final String Function(String sort)? getSortDescription;
  final String Function(String sort)? getHumanReadableSortName;
  final String searchHintText;
  final List<Widget> searchBarActions;
  final double searchBarHeight;

  final List<AppDataColumn> columns;
  final TableCellBuilder<T> cellBuilder;

  final String configKey;
  final List<String> initialPinnedColumns;
  final List<String> initialHiddenColumns;
  final List<String> excludeFromPin;
  final List<String> excludeFromHide;
  final int maxPinnedColumns;

  final String emptyTitle;
  final String emptyDescription;
  final IconData emptyIcon;

  final void Function(T item)? onRowTap;
  final double rowHeight;

  final bool requireSelects;
  final bool requirePin;
  final bool requireExpandableColumnWidth;
  final bool requireColumnSettings;

  final String Function(T item)? selectionIdExtractor;
  final String Function(T item)? selectionLabelExtractor;
  final void Function(Map<String, String> selection)? onSelectionChanged;
  final Map<String, String> initialSelection;
  final double selectColumnWidth;
  final Future<bool> Function(String id)? onBulkDeleteItem;
  final VoidCallback? onBulkDeleteComplete;
  final BulkActionsBuilder? bulkActionsBuilder;

  const AppDataTable({
    super.key,
    required this.items,
    required this.currentPage,
    required this.totalPages,
    required this.totalItems,
    required this.columns,
    required this.cellBuilder,
    required this.configKey,
    this.isLoading = false,
    this.isOperationInProgress = false,
    this.onFetchData,
    this.sortByOptions = const [],
    this.filterByOptions = const [],
    this.currentSortBy,
    this.currentSortOrder,
    this.currentFilters = const {},
    this.getHumanReadableFilterName,
    this.filterValueOptions,
    this.getFilterValueLabel,
    this.isDateRangeFilter,
    this.getFilterDescription,
    this.getSortDescription,
    this.getHumanReadableSortName,
    this.searchHintText = AppStrings.SEARCH,
    this.searchBarActions = const [],
    this.searchBarHeight = AppSizes.tableSearchBarHeight,
    this.initialPinnedColumns = const [],
    this.initialHiddenColumns = const [],
    this.excludeFromPin = const [],
    this.excludeFromHide = const [AppStrings.TABLE_ACTIONS_COLUMN_LABEL],
    this.maxPinnedColumns = 5,
    this.emptyTitle = AppStrings.TABLE_EMPTY_TITLE,
    this.emptyDescription = AppStrings.TABLE_EMPTY_BODY,
    this.emptyIcon = Icons.search_off_rounded,
    this.onRowTap,
    this.rowHeight = AppSizes.tableRowHeight,
    this.requireSelects = false,
    this.requirePin = true,
    this.requireExpandableColumnWidth = true,
    this.requireColumnSettings = true,
    this.selectionIdExtractor,
    this.selectionLabelExtractor,
    this.onSelectionChanged,
    this.initialSelection = const {},
    this.selectColumnWidth = AppSizes.tableSelectColumnWidth,
    this.onBulkDeleteItem,
    this.onBulkDeleteComplete,
    this.bulkActionsBuilder,
  }) : assert(
         !requireSelects || selectionIdExtractor != null,
         'selectionIdExtractor is required when requireSelects is true.',
       );

  @override
  State<AppDataTable<T>> createState() => AppDataTableState<T>();
}

class AppDataTableState<T> extends State<AppDataTable<T>> {
  late final TextEditingController _searchController;
  late final ScrollController _bodyScrollController;
  late final ValueNotifier<Map<String, String>> _selectionNotifier;

  final Map<String, String> _selection = {};
  final Map<String, double> _columnWidthOverrides = {};

  List<String> _pinnedColumns = [];
  List<String> _hiddenColumns = [];

  int _itemsPerPage = 0;
  bool _isScrolled = false;
  bool _isAtEnd = false;
  bool _isHoveringScroll = false;
  bool _hasResized = false;

  Set<String> get selectedIds => _selection.keys.toSet();

  Map<String, String> get selectedLabels => Map.unmodifiable(_selection);

  ValueListenable<Map<String, String>> get selectionListenable =>
      _selectionNotifier;

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
    _bodyScrollController = ScrollController();
    _pinnedColumns = List<String>.from(widget.initialPinnedColumns);
    _hiddenColumns = List<String>.from(widget.initialHiddenColumns);
    _selection.addAll(widget.initialSelection);
    _selectionNotifier = ValueNotifier<Map<String, String>>(Map.of(_selection));
    _bodyScrollController.addListener(_onBodyScroll);
    _loadConfig();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _bodyScrollController.removeListener(_onBodyScroll);
    _bodyScrollController.dispose();
    _selectionNotifier.dispose();
    super.dispose();
  }

  void _onBodyScroll() {
    if (!_bodyScrollController.hasClients) return;
    final bool scrolled = _bodyScrollController.offset > 0;
    final bool atEnd =
        _bodyScrollController.offset >=
        _bodyScrollController.position.maxScrollExtent - AppSpacing.sm;
    if (scrolled != _isScrolled || atEnd != _isAtEnd) {
      setState(() {
        _isScrolled = scrolled;
        _isAtEnd = atEnd;
      });
    }
  }

  Future<void> _loadConfig() async {
    final Map<String, dynamic>? config = await StorageService.getTableConfig(
      widget.configKey,
    );
    if (config == null || !mounted) return;

    setState(() {
      final dynamic pinned = config[AppDataTable.CONFIG_PINNED_KEY];
      if (pinned is List && widget.requirePin) {
        _pinnedColumns = pinned.whereType<String>().toList()
          ..removeWhere(_isSelectColumn);
        final String? firstColumn = widget.columns.isNotEmpty
            ? widget.columns.first.id
            : null;
        if (firstColumn != null && !_pinnedColumns.contains(firstColumn)) {
          _pinnedColumns.insert(0, firstColumn);
        }
      }
      final dynamic hidden = config[AppDataTable.CONFIG_HIDDEN_KEY];
      if (hidden is List) {
        _hiddenColumns = hidden.whereType<String>().toList()
          ..removeWhere(_isSelectColumn);
      }
    });
  }

  void _saveConfig() {
    StorageService.saveTableConfig(widget.configKey, {
      AppDataTable.CONFIG_PINNED_KEY: _pinnedColumns,
      AppDataTable.CONFIG_HIDDEN_KEY: _hiddenColumns,
    });
  }

  String _idOf(T item) => widget.selectionIdExtractor!(item);

  String _labelOf(T item) =>
      widget.selectionLabelExtractor?.call(item) ?? _idOf(item);

  void _emitSelection() {
    _selectionNotifier.value = Map.of(_selection);
    widget.onSelectionChanged?.call(Map.of(_selection));
  }

  void clearSelection() {
    if (_selection.isEmpty) return;
    setState(_selection.clear);
    _emitSelection();
  }

  void setItemSelected(T item, bool selected) {
    final String id = _idOf(item);
    setState(() {
      if (selected) {
        _selection[id] = _labelOf(item);
      } else {
        _selection.remove(id);
      }
    });
    _emitSelection();
  }

  void setPageSelected(bool selected) {
    setState(() {
      for (final item in widget.items) {
        final String id = _idOf(item);
        if (selected) {
          _selection[id] = _labelOf(item);
        } else {
          _selection.remove(id);
        }
      }
    });
    _emitSelection();
  }

  bool get _allCurrentPageSelected =>
      widget.items.isNotEmpty &&
      widget.items.every((item) => _selection.containsKey(_idOf(item)));

  bool get _someSelected => _selection.isNotEmpty && !_allCurrentPageSelected;

  bool _isSelectColumn(String columnId) =>
      widget.requireSelects && columnId == AppDataTable.SELECT_COLUMN_ID;

  List<String> get _effectiveExcludeFromHide => widget.requireSelects
      ? [...widget.excludeFromHide, AppDataTable.SELECT_COLUMN_ID]
      : widget.excludeFromHide;

  List<String> get _effectiveExcludeFromPin => widget.requireSelects
      ? [...widget.excludeFromPin, AppDataTable.SELECT_COLUMN_ID]
      : widget.excludeFromPin;

  List<AppDataColumn> get _allColumns => widget.requireSelects
      ? [
          AppDataColumn(
            id: AppDataTable.SELECT_COLUMN_ID,
            label: AppStrings.TABLE_SELECT_COLUMN_LABEL,
            width: widget.selectColumnWidth,
            isCenter: true,
          ),
          ...widget.columns,
        ]
      : widget.columns;

  List<AppDataColumn> get _visibleColumns =>
      _allColumns.where((col) => !_hiddenColumns.contains(col.id)).toList();

  List<AppDataColumn> get _stickyColumns {
    final Iterable<AppDataColumn> selectColumn = widget.requireSelects
        ? _visibleColumns.where((col) => _isSelectColumn(col.id))
        : const <AppDataColumn>[];
    final Iterable<AppDataColumn> pinnedColumns = widget.requirePin
        ? _visibleColumns.where(
            (col) =>
                _pinnedColumns.contains(col.id) && !_isSelectColumn(col.id),
          )
        : const <AppDataColumn>[];
    return [...selectColumn, ...pinnedColumns];
  }

  List<AppDataColumn> get _scrollableColumns => widget.requirePin
      ? _visibleColumns
            .where(
              (col) =>
                  !_pinnedColumns.contains(col.id) && !_isSelectColumn(col.id),
            )
            .toList()
      : _visibleColumns.where((col) => !_isSelectColumn(col.id)).toList();

  void _togglePinned(String columnId) {
    if (!widget.requirePin || _isSelectColumn(columnId)) return;

    if (_pinnedColumns.contains(columnId)) {
      final String? firstColumn = widget.columns.isNotEmpty
          ? widget.columns.first.id
          : null;
      if (columnId == firstColumn) return;
      setState(() => _pinnedColumns.remove(columnId));
      _saveConfig();
      return;
    }

    if (_pinnedColumns.length >= widget.maxPinnedColumns) {
      ToastUtils.showWarning(
        context,
        AppStrings.TABLE_PIN_LIMIT_TITLE,
        description: AppStrings.TABLE_PIN_LIMIT_BODY,
      );
      return;
    }

    setState(() => _pinnedColumns.add(columnId));
    _saveConfig();
  }

  void _toggleHidden(String columnId) {
    if (!widget.requireColumnSettings || _isSelectColumn(columnId)) return;
    if (_effectiveExcludeFromHide.contains(columnId)) return;
    setState(() {
      if (_hiddenColumns.contains(columnId)) {
        _hiddenColumns.remove(columnId);
      } else {
        _pinnedColumns.remove(columnId);
        _hiddenColumns.add(columnId);
      }
    });
    _saveConfig();
  }

  void showColumnSettings() {
    if (!widget.requireColumnSettings) return;
    showDialog<void>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (dialogContext) => ColumnSettingsDialog(
        columns: _allColumns,
        hiddenColumns: _hiddenColumns,
        excludedColumnIds: _effectiveExcludeFromHide,
        onToggle: _toggleHidden,
      ),
    );
  }

  void _resizeColumn(String columnId, double delta) {
    if (!widget.requireExpandableColumnWidth) return;
    final int index = _allColumns.indexWhere((col) => col.id == columnId);
    if (index == -1) return;

    setState(() {
      _hasResized = true;
      final double current =
          _columnWidthOverrides[columnId] ?? _allColumns[index].width;
      _columnWidthOverrides[columnId] = ColumnResizeHandle.clampWidth(
        current,
        delta,
        minWidth: ColumnResizeHandle.minWidthFor(columnId),
      );
    });
  }

  double _effectiveWidth(AppDataColumn col) =>
      _columnWidthOverrides[col.id] ?? col.width;

  double _effectiveColumnsWidth(List<AppDataColumn> cols) =>
      cols.fold(0.0, (sum, col) => sum + _effectiveWidth(col));

  double _dividerTotal(int columnCount) =>
      columnCount * AppSizes.tableResizeHandleWidth;

  String? get _searchQuery =>
      _searchController.text.isNotEmpty ? _searchController.text : null;

  void _onSearch({
    required String search,
    required String? sortBy,
    required String? sortOrder,
    required Map<String, String> filters,
  }) {
    widget.onFetchData?.call(
      page: 1,
      limit: _itemsPerPage,
      search: search.isNotEmpty ? search : null,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: AppFilterSearchBar(
                  controller: _searchController,
                  hintText: widget.searchHintText,
                  sortByOptions: widget.sortByOptions,
                  filterByOptions: widget.filterByOptions,
                  filterValueOptions: widget.filterValueOptions,
                  getFilterValueLabel: widget.getFilterValueLabel,
                  isDateRangeFilter: widget.isDateRangeFilter,
                  getFilterDescription: widget.getFilterDescription,
                  getSortDescription: widget.getSortDescription,
                  initialSortBy: widget.currentSortBy,
                  initialSortOrder: widget.currentSortOrder,
                  initialFilters: widget.currentFilters,
                  getHumanReadableFilterName:
                      widget.getHumanReadableFilterName ?? (value) => value,
                  getHumanReadableSortName:
                      widget.getHumanReadableSortName ?? (value) => value,
                  onSearch: _onSearch,
                  minHeight: widget.searchBarHeight,
                ),
              ),
              for (final action in widget.searchBarActions) ...[
                const SizedBox(width: AppSpacing.smd),
                Align(
                  alignment: Alignment.topCenter,
                  child: SizedBox(
                    width: widget.searchBarHeight,
                    height: widget.searchBarHeight,
                    child: action,
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.smd),
        Expanded(
          child: Stack(
            children: [
              Positioned.fill(child: _buildTableArea()),
              if (widget.requireSelects && _selection.isNotEmpty)
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: AppSpacing.lg,
                  child: Center(child: _buildSelectionBar()),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTableArea() {
    return ResponsiveTableLayout(
      rowHeight: widget.rowHeight,
      overheadHeight: AppSizes.tableOverheadHeight,
      builder: (context, itemsPerPage) {
        if (_itemsPerPage != itemsPerPage && itemsPerPage > 0) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (!mounted || _itemsPerPage == itemsPerPage) return;
            final bool isInitialLoad = _itemsPerPage == 0;
            setState(() => _itemsPerPage = itemsPerPage);
            if (isInitialLoad) {
              widget.onFetchData?.call(
                page: widget.currentPage,
                limit: itemsPerPage,
                search: _searchQuery,
                sortBy: widget.currentSortBy,
                sortOrder: widget.currentSortOrder,
                filters: widget.currentFilters,
              );
            }
          });
        }
        return LayoutBuilder(
          builder: (layoutContext, constraints) => ScrollConfiguration(
            behavior: const AppScrollBehavior(),
            child: _buildTableContainer(widget.items, constraints.maxWidth),
          ),
        );
      },
    );
  }

  Widget _buildSelectionBar() {
    final int count = _selection.length;
    return Material(
      color: AppColors.TRANSPARENT,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.sm,
        ),
        constraints: const BoxConstraints(
          maxWidth: AppSizes.tableSelectionBarMaxWidth,
        ),
        decoration: BoxDecoration(
          color: AppColors.SURFACE,
          borderRadius: BorderRadius.circular(AppRadius.lg),
          border: Border.all(color: AppColors.PRIMARY),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            MouseRegion(
              cursor: SystemMouseCursors.click,
              child: Tooltip(
                message: AppStrings.TABLE_CLEAR_SELECTION,
                child: GestureDetector(
                  onTap: clearSelection,
                  child: const Icon(
                    Icons.close_rounded,
                    size: AppSizes.iconMd,
                    color: AppColors.PRIMARY,
                  ),
                ),
              ),
            ),
            const SizedBox(width: AppSpacing.smd),
            Flexible(
              child: Text(
                '$count ${count == 1 ? AppStrings.TABLE_ITEM_SELECTED_SINGULAR : AppStrings.TABLE_ITEM_SELECTED_PLURAL}',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTypography.labelMedium.copyWith(
                  color: AppColors.PRIMARY,
                ),
              ),
            ),
            if (widget.bulkActionsBuilder != null) ...[
              const SizedBox(width: AppSpacing.md),
              widget.bulkActionsBuilder!(
                context,
                Map<String, String>.unmodifiable(_selection),
                () {
                  clearSelection();
                  widget.onBulkDeleteComplete?.call();
                },
              ),
            ] else if (widget.onBulkDeleteItem != null) ...[
              const SizedBox(width: AppSpacing.md),
              BulkActionButtons(
                selectionListenable: _selectionNotifier,
                onDeleteItem: widget.onBulkDeleteItem,
                onComplete: () {
                  clearSelection();
                  widget.onBulkDeleteComplete?.call();
                },
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTableContainer(List<T> data, double maxWidth) {
    final List<AppDataColumn> stickyCols = _stickyColumns;
    final List<AppDataColumn> scrollCols = _scrollableColumns;
    final List<AppDataColumn> visibleCols = [...stickyCols, ...scrollCols];

    final double preferredContentWidth = _effectiveColumnsWidth(visibleCols);
    final double dividersWidth = _dividerTotal(visibleCols.length);
    final double totalPreferredWidth = preferredContentWidth + dividersWidth;

    final bool needsFilling =
        !_hasResized &&
        preferredContentWidth > 0 &&
        totalPreferredWidth < maxWidth;
    final double scaleFactor = needsFilling
        ? (maxWidth - dividersWidth) / preferredContentWidth
        : 1.0;
    final double renderedWidth =
        (preferredContentWidth * scaleFactor) + dividersWidth;

    final bool isBusy = widget.isLoading || widget.isOperationInProgress;
    final bool showShimmer =
        widget.isLoading || (data.isEmpty && _itemsPerPage == 0);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.SURFACE,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.BORDER),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          _buildHeader(scaleFactor, needsFilling, maxWidth, renderedWidth),
          Expanded(
            child: Stack(
              children: [
                if (showShimmer)
                  Padding(
                    padding: const EdgeInsets.all(AppSpacing.md),
                    child: ShimmerRows(
                      rowCount: _itemsPerPage > 0 ? _itemsPerPage : 8,
                      columnFlex: List<int>.filled(
                        visibleCols.isEmpty ? 1 : visibleCols.length,
                        1,
                      ),
                    ),
                  )
                else
                  Opacity(
                    opacity: isBusy ? 0.7 : 1.0,
                    child: _buildTableBody(
                      data,
                      stickyCols,
                      scrollCols,
                      scaleFactor,
                      needsFilling,
                      maxWidth,
                      renderedWidth,
                    ),
                  ),
                if (!needsFilling && data.isNotEmpty)
                  Positioned(
                    left: 0,
                    right: 0,
                    bottom: 0,
                    child: _buildScrollStrip(maxWidth),
                  ),
                if (!needsFilling && !_isAtEnd && data.isNotEmpty)
                  Positioned(
                    right: AppSpacing.lgs,
                    bottom: AppSpacing.xl,
                    child: const _ScrollHintChip(),
                  ),
              ],
            ),
          ),
          if (isBusy && data.isNotEmpty)
            const LinearProgressIndicator(
              minHeight: AppSizes.tableProgressHeight,
              backgroundColor: AppColors.TRANSPARENT,
              valueColor: AlwaysStoppedAnimation<Color>(AppColors.PRIMARY),
            ),
          if (widget.totalPages > 0)
            AppPagination(
              currentPage: widget.currentPage,
              totalPages: widget.totalPages,
              totalItems: widget.totalItems,
              itemsPerPage: _itemsPerPage,
              onPageChanged: (page) => widget.onFetchData?.call(
                page: page,
                limit: _itemsPerPage,
                search: _searchQuery,
                sortBy: widget.currentSortBy,
                sortOrder: widget.currentSortOrder,
                filters: widget.currentFilters,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildHeader(
    double scaleFactor,
    bool needsFilling,
    double maxWidth,
    double renderedWidth,
  ) {
    final List<AppDataColumn> stickyCols = _stickyColumns;
    final List<AppDataColumn> scrollCols = _scrollableColumns;
    final double stickyWidth =
        (_effectiveColumnsWidth(stickyCols) * scaleFactor) +
        _dividerTotal(stickyCols.length);

    return SelectionContainer.disabled(
      child: Container(
        height: AppSizes.tableHeaderHeight,
        decoration: const BoxDecoration(
          color: AppColors.TABLE_HEADER_BG,
          border: Border(bottom: BorderSide(color: AppColors.DIVIDER)),
        ),
        child: ClipRect(
          child: Stack(
            children: [
              AnimatedBuilder(
                animation: _bodyScrollController,
                builder: (context, child) {
                  final double offset = _bodyScrollController.hasClients
                      ? _bodyScrollController.offset
                      : 0.0;
                  return TableHeaderScrollLayer(
                    offset: offset,
                    width: needsFilling ? maxWidth : renderedWidth,
                    child: child!,
                  );
                },
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SizedBox(width: stickyWidth),
                    ...scrollCols.map(
                      (col) => _buildHeaderCell(col, scaleFactor: scaleFactor),
                    ),
                  ],
                ),
              ),
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                child: ColoredBox(
                  color: AppColors.TABLE_HEADER_BG,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: stickyCols
                        .map(
                          (col) =>
                              _buildHeaderCell(col, scaleFactor: scaleFactor),
                        )
                        .toList(),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCell(AppDataColumn col, {double scaleFactor = 1.0}) {
    final bool isPinned = _pinnedColumns.contains(col.id);
    final bool showPinControl =
        widget.requirePin && !_effectiveExcludeFromPin.contains(col.id);
    final double finalWidth = _effectiveWidth(col) * scaleFactor;

    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(
          width: finalWidth,
          child: Stack(
            children: [
              if (_isSelectColumn(col.id))
                Center(child: _buildSelectAllCheckbox())
              else
                Container(
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.smd,
                  ),
                  child: Text(
                    col.label,
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.tableHeader,
                  ),
                ),
              if (showPinControl)
                Positioned(
                  right: AppSpacing.xs,
                  top: AppSpacing.xs,
                  child: MouseRegion(
                    cursor: SystemMouseCursors.click,
                    child: Tooltip(
                      message: isPinned
                          ? AppStrings.TABLE_UNPIN_COLUMN
                          : AppStrings.TABLE_PIN_COLUMN,
                      child: GestureDetector(
                        onTap: () => _togglePinned(col.id),
                        child: Icon(
                          isPinned
                              ? Icons.push_pin_rounded
                              : Icons.push_pin_outlined,
                          size: AppSizes.tablePinIconSize,
                          color: isPinned
                              ? AppColors.TEXT_ON_PRIMARY
                              : AppColors.TABLE_HEADER_PIN_IDLE,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        if (widget.requireExpandableColumnWidth && !_isSelectColumn(col.id))
          ColumnResizeHandle(onDrag: (delta) => _resizeColumn(col.id, delta))
        else
          const SizedBox(width: AppSizes.tableResizeHandleWidth),
      ],
    );
  }

  Widget _buildSelectAllCheckbox() {
    return Tooltip(
      message: AppStrings.TABLE_SELECT_ALL_ON_PAGE,
      child: Checkbox(
        value: _someSelected ? null : _allCurrentPageSelected,
        tristate: true,
        onChanged: (value) => setPageSelected(value == true),
        activeColor: AppColors.WHITE,
        checkColor: AppColors.PRIMARY,
        side: const BorderSide(
          color: AppColors.WHITE,
          width: AppSizes.borderMedium,
        ),
      ),
    );
  }

  Widget _buildRowCheckbox(T item) {
    return Tooltip(
      message: AppStrings.TABLE_SELECT_ROW,
      child: Checkbox(
        value: _selection.containsKey(_idOf(item)),
        onChanged: (value) => setItemSelected(item, value == true),
        activeColor: AppColors.PRIMARY,
        checkColor: AppColors.TEXT_ON_PRIMARY,
        side: const BorderSide(
          color: AppColors.BORDER_STRONG,
          width: AppSizes.borderMedium,
        ),
      ),
    );
  }

  Widget _buildTableBody(
    List<T> data,
    List<AppDataColumn> stickyCols,
    List<AppDataColumn> scrollCols,
    double scaleFactor,
    bool needsFilling,
    double maxWidth,
    double renderedWidth,
  ) {
    if (data.isEmpty) {
      return EmptyState(
        icon: widget.emptyIcon,
        title: widget.emptyTitle,
        subtitle: widget.emptyDescription,
      );
    }

    return SingleChildScrollView(
      controller: _bodyScrollController,
      scrollDirection: Axis.horizontal,
      physics: needsFilling
          ? const NeverScrollableScrollPhysics()
          : const ClampingScrollPhysics(),
      child: SizedBox(
        width: needsFilling ? maxWidth : renderedWidth,
        child: Padding(
          padding: const EdgeInsets.only(bottom: AppSpacing.smd),
          child: ListView.builder(
            itemCount: data.length,
            itemExtent: widget.rowHeight,
            itemBuilder: (context, index) => _TableRow<T>(
              item: data[index],
              stickyColumns: stickyCols,
              scrollableColumns: scrollCols,
              scaleFactor: scaleFactor,
              rowHeight: widget.rowHeight,
              isBusy: widget.isLoading || widget.isOperationInProgress,
              scrollController: _bodyScrollController,
              onTap: widget.onRowTap,
              stickyWidth:
                  (_effectiveColumnsWidth(stickyCols) * scaleFactor) +
                  _dividerTotal(stickyCols.length),
              cellBuilder: _buildDataCell,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDataCell(
    BuildContext context,
    AppDataColumn col,
    T item,
    double scaleFactor,
  ) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: _effectiveWidth(col) * scaleFactor,
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
          alignment: Alignment.center,
          child: _isSelectColumn(col.id)
              ? _buildRowCheckbox(item)
              : widget.cellBuilder(context, item, col),
        ),
        const ColumnBodyDivider(),
      ],
    );
  }

  Widget _buildScrollStrip(double maxWidth) {
    return AnimatedBuilder(
      animation: _bodyScrollController,
      builder: (context, child) {
        if (!_bodyScrollController.hasClients ||
            !_bodyScrollController.position.hasContentDimensions) {
          return const SizedBox.shrink();
        }
        final double maxScroll = _bodyScrollController.position.maxScrollExtent;
        if (maxScroll <= 0) return const SizedBox.shrink();

        final double currentScroll = _bodyScrollController.offset;
        final double thumbWidth =
            (maxWidth / (maxWidth + maxScroll)) * maxWidth;
        final double trackWidth =
            maxWidth - (AppSizes.tableScrollTrackInset * 2);
        final double thumbOffset =
            (currentScroll / maxScroll) * (trackWidth - thumbWidth);

        return MouseRegion(
          onEnter: (_) => setState(() => _isHoveringScroll = true),
          onExit: (_) => setState(() => _isHoveringScroll = false),
          child: SizedBox(
            height: _isHoveringScroll
                ? AppSizes.tableScrollStripHoverHeight
                : AppSizes.tableScrollStripHeight,
            child: DecoratedBox(
              decoration: const BoxDecoration(
                color: AppColors.SURFACE,
                border: Border(
                  top: BorderSide(
                    color: AppColors.DIVIDER,
                    width: AppSizes.dividerThin,
                  ),
                ),
              ),
              child: Stack(
                children: [
                  Positioned.fill(
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onTapDown: (details) {
                        final double clickPosition =
                            details.localPosition.dx -
                            AppSizes.tableScrollTrackInset;
                        final double target =
                            (clickPosition / (trackWidth - thumbWidth)).clamp(
                              0.0,
                              1.0,
                            );
                        _bodyScrollController.jumpTo(target * maxScroll);
                      },
                      child: Center(
                        child: Container(
                          height: _isHoveringScroll
                              ? AppSizes.tableScrollThumbHoverHeight
                              : AppSizes.tableScrollThumbHeight,
                          margin: const EdgeInsets.symmetric(
                            horizontal: AppSizes.tableScrollTrackInset,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.TABLE_SCROLL_TRACK,
                            borderRadius: BorderRadius.circular(AppRadius.xs),
                          ),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    left: AppSizes.tableScrollTrackInset + thumbOffset,
                    top: AppSpacing.xxs,
                    bottom: AppSpacing.xxs,
                    child: GestureDetector(
                      behavior: HitTestBehavior.opaque,
                      onHorizontalDragUpdate: (details) {
                        final double ratio =
                            maxScroll / (trackWidth - thumbWidth);
                        _bodyScrollController.jumpTo(
                          (_bodyScrollController.offset +
                                  (details.delta.dx * ratio))
                              .clamp(0.0, maxScroll),
                        );
                      },
                      child: MouseRegion(
                        cursor: SystemMouseCursors.grab,
                        child: Container(
                          width: thumbWidth.clamp(
                            AppSizes.tableScrollThumbMinWidth,
                            double.infinity,
                          ),
                          decoration: BoxDecoration(
                            color: _isHoveringScroll
                                ? AppColors.TABLE_SCROLL_THUMB_ACTIVE
                                : AppColors.TABLE_SCROLL_THUMB,
                            borderRadius: BorderRadius.circular(AppRadius.md),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _ScrollHintChip extends StatelessWidget {
  const _ScrollHintChip();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.smd,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: AppColors.PRIMARY,
        borderRadius: BorderRadius.circular(AppRadius.full),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.arrow_forward_rounded,
            color: AppColors.TEXT_ON_PRIMARY,
            size: AppSizes.iconSm,
          ),
          const SizedBox(width: AppSpacing.xs),
          Text(
            AppStrings.TABLE_SCROLL_HINT,
            style: AppTypography.labelSmall.copyWith(
              color: AppColors.TEXT_ON_PRIMARY,
            ),
          ),
        ],
      ),
    );
  }
}

class _TableRow<T> extends StatefulWidget {
  final T item;
  final List<AppDataColumn> stickyColumns;
  final List<AppDataColumn> scrollableColumns;
  final double scaleFactor;
  final double rowHeight;
  final double stickyWidth;
  final bool isBusy;
  final ScrollController scrollController;
  final void Function(T item)? onTap;
  final Widget Function(
    BuildContext context,
    AppDataColumn column,
    T item,
    double scaleFactor,
  )
  cellBuilder;

  const _TableRow({
    required this.item,
    required this.stickyColumns,
    required this.scrollableColumns,
    required this.scaleFactor,
    required this.rowHeight,
    required this.stickyWidth,
    required this.isBusy,
    required this.scrollController,
    required this.onTap,
    required this.cellBuilder,
  });

  @override
  State<_TableRow<T>> createState() => _TableRowState<T>();
}

class _TableRowState<T> extends State<_TableRow<T>> {
  bool _isHovered = false;

  bool get _isInteractive => widget.onTap != null && !widget.isBusy;

  @override
  Widget build(BuildContext context) {
    final Color background = _isHovered && _isInteractive
        ? AppColors.TABLE_ROW_HOVER
        : AppColors.SURFACE;

    return MouseRegion(
      cursor: _isInteractive
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: _isInteractive ? () => widget.onTap!(widget.item) : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 160),
          curve: Curves.easeOutCubic,
          height: widget.rowHeight,
          decoration: BoxDecoration(
            color: background,
            border: const Border(
              bottom: BorderSide(
                color: AppColors.TABLE_ROW_DIVIDER,
                width: AppSizes.dividerThin,
              ),
            ),
          ),
          child: Stack(
            children: [
              Row(
                children: [
                  SizedBox(width: widget.stickyWidth),
                  ...widget.scrollableColumns.map(
                    (col) => widget.cellBuilder(
                      context,
                      col,
                      widget.item,
                      widget.scaleFactor,
                    ),
                  ),
                ],
              ),
              if (widget.stickyColumns.isNotEmpty)
                AnimatedBuilder(
                  animation: widget.scrollController,
                  builder: (context, child) {
                    final double offset = widget.scrollController.hasClients
                        ? widget.scrollController.offset
                        : 0.0;
                    return Positioned(
                      left: offset,
                      top: 0,
                      bottom: 0,
                      child: ColoredBox(color: background, child: child!),
                    );
                  },
                  child: Row(
                    children: widget.stickyColumns
                        .map(
                          (col) => widget.cellBuilder(
                            context,
                            col,
                            widget.item,
                            widget.scaleFactor,
                          ),
                        )
                        .toList(),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
