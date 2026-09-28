import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

enum RowActionTone { neutral, success, warning, error }

class RowAction {
  final String label;
  final IconData icon;
  final RowActionTone tone;
  final VoidCallback? onSelected;

  /// Shown instead of [label] as a hint when the action is unavailable.
  final String? blockedHint;

  const RowAction({
    required this.label,
    required this.icon,
    required this.onSelected,
    this.tone = RowActionTone.neutral,
    this.blockedHint,
  });

  bool get isEnabled => onSelected != null;
}

class RowActionsMenu extends StatefulWidget {
  final List<RowAction> actions;
  final bool enabled;

  const RowActionsMenu({
    super.key,
    required this.actions,
    this.enabled = true,
  });

  @override
  State<RowActionsMenu> createState() => _RowActionsMenuState();
}

class _RowActionsMenuState extends State<RowActionsMenu> {
  final LayerLink _layerLink = LayerLink();

  OverlayEntry? _overlayEntry;
  bool _isHovered = false;

  @override
  void dispose() {
    _removeOverlay();
    super.dispose();
  }

  void _removeOverlay() {
    _overlayEntry?.remove();
    _overlayEntry = null;
  }

  void _toggle() {
    if (!widget.enabled) return;
    if (_overlayEntry != null) {
      _removeOverlay();
      return;
    }

    _overlayEntry = OverlayEntry(builder: _buildOverlay);
    Overlay.of(context).insert(_overlayEntry!);
  }

  void _select(RowAction action) {
    _removeOverlay();
    action.onSelected?.call();
  }

  /// Rough height of the popup: enough to decide which way it should open
  /// without laying it out first. Item height is the tallest realistic case
  /// (label plus a blocked-reason line).
  double get _estimatedHeight {
    final int blocked = widget.actions
        .where((action) => action.onSelected == null)
        .length;
    return (widget.actions.length * AppSizes.rowActionItemHeight) +
        (blocked * AppSizes.rowActionHintHeight) +
        (AppSpacing.xs * 2);
  }

  /// A row near the foot of the table has no room below it, so the menu
  /// opens upward instead of being clipped by the table's edge.
  bool _opensUpward(BuildContext overlayContext) {
    final RenderObject? box = context.findRenderObject();
    if (box is! RenderBox || !box.hasSize) return false;

    final double top = box.localToGlobal(Offset.zero).dy;
    final double bottom = top + box.size.height;
    final double below = MediaQuery.sizeOf(overlayContext).height - bottom;

    if (below >= _estimatedHeight + AppSpacing.xs) return false;
    return top > below;
  }

  Widget _buildOverlay(BuildContext overlayContext) {
    final bool opensUpward = _opensUpward(overlayContext);

    return Stack(
      children: [
        Positioned.fill(
          child: GestureDetector(
            behavior: HitTestBehavior.translucent,
            onTap: _removeOverlay,
          ),
        ),
        Positioned(
          width: AppSizes.rowActionsMenuWidth,
          child: CompositedTransformFollower(
            link: _layerLink,
            showWhenUnlinked: false,
            targetAnchor: opensUpward
                ? Alignment.topRight
                : Alignment.bottomRight,
            followerAnchor: opensUpward
                ? Alignment.bottomRight
                : Alignment.topRight,
            offset: Offset(0, opensUpward ? -AppSpacing.xs : AppSpacing.xs),
            child: Material(
              color: AppColors.TRANSPARENT,
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
                decoration: BoxDecoration(
                  color: AppColors.SURFACE,
                  border: Border.all(color: AppColors.BORDER),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final action in widget.actions)
                      _MenuItem(
                        action: action,
                        onTap: () => _select(action),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final bool isActive = _overlayEntry != null;
    final Color accent = widget.enabled
        ? AppColors.PRIMARY
        : AppColors.TEXT_DISABLED;

    return CompositedTransformTarget(
      link: _layerLink,
      child: MouseRegion(
        cursor: widget.enabled
            ? SystemMouseCursors.click
            : SystemMouseCursors.basic,
        onEnter: (_) => setState(() => _isHovered = true),
        onExit: (_) => setState(() => _isHovered = false),
        child: GestureDetector(
          onTap: _toggle,
          child: Tooltip(
            message: AppStrings.TABLE_ROW_ACTIONS_TOOLTIP,
            child: Container(
              height: AppSizes.tableActionButtonHeight,
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.smd),
              decoration: BoxDecoration(
                color: _isHovered || isActive
                    ? AppColors.PRIMARY_SURFACE
                    : AppColors.TRANSPARENT,
                border: Border.all(color: accent),
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    AppStrings.TABLE_ROW_ACTIONS,
                    style: AppTypography.button.copyWith(color: accent),
                  ),
                  const SizedBox(width: AppSpacing.xs),
                  Icon(
                    isActive
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    size: AppSizes.iconSm,
                    color: accent,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _MenuItem extends StatefulWidget {
  final RowAction action;
  final VoidCallback onTap;

  const _MenuItem({required this.action, required this.onTap});

  @override
  State<_MenuItem> createState() => _MenuItemState();
}

class _MenuItemState extends State<_MenuItem> {
  bool _isHovered = false;

  Color get _foreground {
    if (!widget.action.isEnabled) return AppColors.TEXT_DISABLED;

    switch (widget.action.tone) {
      case RowActionTone.success:
        return AppColors.SUCCESS;
      case RowActionTone.warning:
        return AppColors.WARNING;
      case RowActionTone.error:
        return AppColors.ERROR;
      case RowActionTone.neutral:
        return AppColors.TEXT_PRIMARY;
    }
  }

  @override
  Widget build(BuildContext context) {
    final RowAction action = widget.action;
    final bool isEnabled = action.isEnabled;

    // No Tooltip here: it drives a LayoutBuilder that cannot resolve a paint
    // transform through the menu's CompositedTransformFollower. The blocked
    // reason is shown inline instead, which is clearer in a menu anyway.
    return MouseRegion(
      cursor: isEnabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: isEnabled ? widget.onTap : null,
        child: Container(
          constraints: const BoxConstraints(
            minHeight: AppSizes.rowActionsItemHeight,
          ),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.smd,
            vertical: AppSpacing.sm,
          ),
          color: _isHovered && isEnabled
              ? AppColors.SIDEBAR_ITEM_HOVER
              : AppColors.TRANSPARENT,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(action.icon, size: AppSizes.iconMd, color: _foreground),
              const SizedBox(width: AppSpacing.smd),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      action.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.bodyMedium.copyWith(
                        color: _foreground,
                      ),
                    ),
                    if (!isEnabled && (action.blockedHint ?? '').isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: AppSpacing.xxs),
                        child: Text(
                          action.blockedHint!,
                          style: AppTypography.caption.copyWith(
                            color: AppColors.TEXT_DISABLED,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
