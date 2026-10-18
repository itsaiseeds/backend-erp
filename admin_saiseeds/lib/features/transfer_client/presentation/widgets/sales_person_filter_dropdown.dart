import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../sales_people/data/models/old_sales_person_model.dart';

/// Unlabeled, compact salesperson picker that fits beside the search bar's
/// trailing slot -- [SearchableField] carries its own label and does not fit
/// that fixed-height strip, so this is a lighter popup built for it alone.
class SalesPersonFilterDropdown extends StatefulWidget {
  final List<OldSalesPersonModel> options;
  final OldSalesPersonModel? value;
  final ValueChanged<OldSalesPersonModel?> onChanged;

  const SalesPersonFilterDropdown({
    super.key,
    required this.options,
    required this.value,
    required this.onChanged,
  });

  @override
  State<SalesPersonFilterDropdown> createState() =>
      _SalesPersonFilterDropdownState();
}

class _SalesPersonFilterDropdownState
    extends State<SalesPersonFilterDropdown> {
  final LayerLink _layerLink = LayerLink();
  final TextEditingController _searchController = TextEditingController();
  OverlayEntry? _overlayEntry;
  bool _isOpen = false;

  @override
  void dispose() {
    _removeOverlay();
    _searchController.dispose();
    super.dispose();
  }

  String _labelFor(OldSalesPersonModel person) => person.isDeleted
      ? '${person.name} ${AppStrings.TRANSFER_CLIENT_SOURCE_DELETED_SUFFIX}'
      : person.name;

  List<OldSalesPersonModel> get _filtered {
    final String query = _searchController.text.trim().toLowerCase();
    if (query.isEmpty) return widget.options;
    return widget.options
        .where((person) => person.name.toLowerCase().contains(query))
        .toList();
  }

  void _toggleMenu() {
    if (_isOpen) {
      _closeMenu();
    } else {
      _openMenu();
    }
  }

  void _openMenu() {
    if (_isOpen) return;
    _searchController.clear();
    _overlayEntry = _buildOverlayEntry();
    Overlay.of(context).insert(_overlayEntry!);
    setState(() => _isOpen = true);
  }

  void _closeMenu() {
    if (!_isOpen) return;
    _removeOverlay();
    setState(() => _isOpen = false);
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  void _select(OldSalesPersonModel? person) {
    widget.onChanged(person);
    _closeMenu();
  }

  OverlayEntry _buildOverlayEntry() {
    return OverlayEntry(
      builder: (context) {
        return Stack(
          children: [
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.translucent,
                onTap: _closeMenu,
              ),
            ),
            CompositedTransformFollower(
              link: _layerLink,
              showWhenUnlinked: false,
              offset: const Offset(0, AppSizes.tableSearchBarHeight + 4),
              child: Material(
                elevation: 8,
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: Container(
                  width: AppSizes.salesPersonDropdownWidth,
                  constraints: const BoxConstraints(
                    maxHeight: AppSizes.salesPersonDropdownMaxHeight,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.SURFACE,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.BORDER),
                  ),
                  child: StatefulBuilder(
                    builder: (context, setMenuState) {
                      return Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(AppSpacing.sm),
                            child: TextField(
                              controller: _searchController,
                              autofocus: true,
                              style: AppTypography.bodySmall,
                              onChanged: (_) => setMenuState(() {}),
                              decoration: InputDecoration(
                                isDense: true,
                                hintText:
                                    AppStrings.TRANSFER_CLIENT_SOURCE_HINT,
                                hintStyle: AppTypography.bodySmall.copyWith(
                                  color: AppColors.TEXT_DISABLED,
                                ),
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: AppSpacing.smd,
                                  vertical: AppSpacing.sm,
                                ),
                                border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(
                                    AppRadius.sm,
                                  ),
                                  borderSide: const BorderSide(
                                    color: AppColors.BORDER,
                                  ),
                                ),
                              ),
                            ),
                          ),
                          const Divider(
                            height: 1,
                            color: AppColors.DIVIDER,
                          ),
                          Flexible(
                            child: ListView(
                              padding: EdgeInsets.zero,
                              shrinkWrap: true,
                              children: [
                                for (final person in _filtered)
                                  _OptionRow(
                                    label: _labelFor(person),
                                    isSelected:
                                        widget.value?.id == person.id,
                                    onTap: () => _select(person),
                                  ),
                                if (_filtered.isEmpty)
                                  Padding(
                                    padding: const EdgeInsets.all(
                                      AppSpacing.md,
                                    ),
                                    child: Text(
                                      AppStrings
                                          .TRANSFER_CLIENT_TARGET_NONE,
                                      style: AppTypography.bodySmall
                                          .copyWith(
                                            color: AppColors.TEXT_SECONDARY,
                                          ),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final OldSalesPersonModel? value = widget.value;

    return CompositedTransformTarget(
      link: _layerLink,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: _toggleMenu,
          child: Container(
            height: AppSizes.tableSearchBarHeight,
            constraints: const BoxConstraints(
              minWidth: AppSizes.salesPersonDropdownTriggerMinWidth,
            ),
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
            decoration: BoxDecoration(
              color: AppColors.SURFACE,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.BORDER),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.person_search_outlined,
                  size: AppSizes.iconSm,
                  color: AppColors.TEXT_SECONDARY,
                ),
                const SizedBox(width: AppSpacing.sm),
                Flexible(
                  child: Text(
                    value == null
                        ? AppStrings.TRANSFER_CLIENT_SOURCE_FIELD
                        : _labelFor(value),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodySmall.copyWith(
                      color: value == null
                          ? AppColors.TEXT_SECONDARY
                          : AppColors.TEXT_PRIMARY,
                      fontWeight: value == null
                          ? FontWeight.w500
                          : FontWeight.w600,
                    ),
                  ),
                ),
                const SizedBox(width: AppSpacing.xs),
                Icon(
                  _isOpen
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.keyboard_arrow_down_rounded,
                  size: AppSizes.iconMd,
                  color: AppColors.TEXT_SECONDARY,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _OptionRow extends StatelessWidget {
  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  const _OptionRow({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: InkWell(
        onTap: onTap,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.smd,
            vertical: AppSpacing.sm,
          ),
          color: isSelected ? AppColors.PRIMARY_SURFACE : null,
          child: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.bodySmall.copyWith(
              color: isSelected ? AppColors.PRIMARY : AppColors.TEXT_PRIMARY,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
        ),
      ),
    );
  }
}
