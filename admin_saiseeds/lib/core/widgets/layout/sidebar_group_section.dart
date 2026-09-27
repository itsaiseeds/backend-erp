import 'package:flutter/material.dart';
import '../../models/sidebar_group_model.dart';
import '../../models/sidebar_item_model.dart';
import '../../constants/font_sizes.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'app_sidebar.dart';

/// A collapsible cluster of sidebar rows under one header.
///
/// In the collapsed rail the header is dropped entirely and the rows render
/// flat: a 72px column has no room for a label, and hiding tabs behind a
/// nameless toggle would make them unreachable.
class SidebarGroupSection extends StatelessWidget {
  final ResolvedSidebarGroup section;
  final String activeItemId;
  final bool isCollapsed;
  final bool isExpanded;
  final ValueChanged<String> onItemSelected;
  final VoidCallback onToggle;

  const SidebarGroupSection({
    super.key,
    required this.section,
    required this.activeItemId,
    required this.isCollapsed,
    required this.isExpanded,
    required this.onItemSelected,
    required this.onToggle,
  });

  @override
  Widget build(BuildContext context) {
    final List<SidebarItemModel> items = section.items;

    if (section.isStandalone || isCollapsed) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final SidebarItemModel item in items)
            SidebarItem(
              item: item,
              isActive: activeItemId == item.id,
              isCollapsed: isCollapsed,
              onTap: () => onItemSelected(item.id),
            ),
        ],
      );
    }

    final bool hasActiveChild = section.containsItem(activeItemId);

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.xs),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          _GroupHeader(
            group: section.group!,
            isExpanded: isExpanded,
            hasActiveChild: hasActiveChild,
            onToggle: onToggle,
          ),
          AnimatedCrossFade(
            firstChild: const SizedBox(width: double.infinity),
            secondChild: _GroupChildren(
              items: items,
              activeItemId: activeItemId,
              onItemSelected: onItemSelected,
            ),
            crossFadeState: isExpanded
                ? CrossFadeState.showSecond
                : CrossFadeState.showFirst,
            duration: const Duration(milliseconds: 200),
            sizeCurve: Curves.easeOutCubic,
            firstCurve: Curves.easeOutCubic,
            secondCurve: Curves.easeOutCubic,
          ),
        ],
      ),
    );
  }
}

class _GroupChildren extends StatelessWidget {
  final List<SidebarItemModel> items;
  final String activeItemId;
  final ValueChanged<String> onItemSelected;

  const _GroupChildren({
    required this.items,
    required this.activeItemId,
    required this.onItemSelected,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: AppSpacing.xs),
      child: Stack(
        children: [
          Positioned(
            top: AppSpacing.xs,
            bottom: AppSpacing.sm,
            left: 0,
            child: Container(
              width: AppSizes.sidebarGroupSpineWidth,
              color: AppColors.SIDEBAR_DIVIDER,
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(left: AppSizes.sidebarGroupIndent),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final SidebarItemModel item in items)
                  SidebarItem(
                    item: item,
                    isActive: activeItemId == item.id,
                    isCollapsed: false,
                    onTap: () => onItemSelected(item.id),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GroupHeader extends StatefulWidget {
  final SidebarGroupModel group;
  final bool isExpanded;
  final bool hasActiveChild;
  final VoidCallback onToggle;

  const _GroupHeader({
    required this.group,
    required this.isExpanded,
    required this.hasActiveChild,
    required this.onToggle,
  });

  @override
  State<_GroupHeader> createState() => _GroupHeaderState();
}

class _GroupHeaderState extends State<_GroupHeader> {
  static const Duration _duration = Duration(milliseconds: 200);

  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    // A collapsed group holding the active tab still has to show where you
    // are, so the header itself carries the accent in that case.
    final bool isParentOfActive =
        !widget.isExpanded && widget.hasActiveChild;

    final Color foreground = isParentOfActive
        ? AppColors.SIDEBAR_ICON_ACTIVE
        : (_isHovered
              ? AppColors.SIDEBAR_TEXT_ACTIVE
              : AppColors.SIDEBAR_TEXT);

    // 11px with tight tracking keeps the longest group name on one line at
    // the 260px sidebar width.
    final TextStyle labelStyle = AppTypography.caption.copyWith(
      color: foreground,
      fontSize: AppFontSizes.FONT_11,
      fontWeight: FontWeight.w700,
      letterSpacing: 0.4,
    );

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: Semantics(
        button: true,
        expanded: widget.isExpanded,
        label: widget.group.label,
        child: GestureDetector(
          onTap: widget.onToggle,
          behavior: HitTestBehavior.opaque,
          child: SizedBox(
            height: AppSizes.sidebarGroupHeaderHeight,
            child: Padding(
              padding: const EdgeInsets.only(
                left: AppSpacing.sm,
                right: AppSpacing.xs,
              ),
              child: Row(
                children: [
                  // The label takes the whole row: a trailing rule competed
                  // for width and truncated names that otherwise fit.
                  Expanded(
                    child: AnimatedDefaultTextStyle(
                      duration: _duration,
                      curve: Curves.easeOutCubic,
                      style: labelStyle,
                      child: Text(
                        widget.group.label.toUpperCase(),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ),
                  if (isParentOfActive) ...[
                    const SizedBox(width: AppSpacing.sm),
                    Container(
                      width: AppSizes.sidebarGroupDotSize,
                      height: AppSizes.sidebarGroupDotSize,
                      decoration: const BoxDecoration(
                        color: AppColors.PRIMARY,
                        shape: BoxShape.circle,
                      ),
                    ),
                  ],
                  const SizedBox(width: AppSpacing.xs),
                  AnimatedRotation(
                    duration: _duration,
                    curve: Curves.easeOutCubic,
                    turns: widget.isExpanded ? 0 : -0.25,
                    child: Icon(
                      Icons.keyboard_arrow_down_rounded,
                      size: AppSizes.sidebarGroupChevron,
                      color: foreground,
                    ),
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
