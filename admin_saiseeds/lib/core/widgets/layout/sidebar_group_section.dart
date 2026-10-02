import 'package:flutter/material.dart';
import '../../constants/font_sizes.dart';
import '../../models/sidebar_item_model.dart';
import '../../models/sidebar_workspace_model.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import 'app_sidebar.dart';

/// A collapsible cluster of sidebar rows under one header.
///
/// In the collapsed rail the header is dropped and the rows render flat: a
/// 72px column has no room for a label, and hiding tabs behind a nameless
/// toggle would make them unreachable.
class SidebarGroupSection extends StatelessWidget {
  final ResolvedSidebarGroup section;
  final String activeItemId;
  final bool isCollapsed;
  final bool isExpanded;
  final ValueChanged<String> onItemSelected;
  final VoidCallback onToggle;

  static const Duration _duration = Duration(milliseconds: 200);

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
        children: [for (final SidebarItemModel item in items) _row(item)],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildHeader(),
        AnimatedSize(
          duration: _duration,
          curve: Curves.easeOutCubic,
          alignment: Alignment.topCenter,
          child: isExpanded
              ? Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    for (final SidebarItemModel item in items) _row(item),
                  ],
                )
              : const SizedBox(width: double.infinity),
        ),
      ],
    );
  }

  Widget _row(SidebarItemModel item) => SidebarItem(
    item: item,
    isActive: item.id == activeItemId,
    isCollapsed: isCollapsed,
    onTap: () => onItemSelected(item.id),
  );

  Widget _buildHeader() {
    // A closed group still shows a dot when the open tab lives inside it,
    // so the current location is never hidden behind a collapsed header.
    final bool hasHiddenActive =
        !isExpanded && section.containsItem(activeItemId);

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onToggle,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.only(
            left: AppSpacing.smd,
            right: AppSpacing.sm,
            top: AppSpacing.smd,
            bottom: AppSpacing.xs,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  section.label ?? '',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.caption.copyWith(
                    fontSize: AppFontSizes.FONT_11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.6,
                    color: AppColors.SIDEBAR_TEXT,
                  ),
                ),
              ),
              if (hasHiddenActive)
                Container(
                  width: AppSizes.sidebarGroupDot,
                  height: AppSizes.sidebarGroupDot,
                  margin: const EdgeInsets.only(right: AppSpacing.xs),
                  decoration: const BoxDecoration(
                    color: AppColors.PRIMARY,
                    shape: BoxShape.circle,
                  ),
                ),
              AnimatedRotation(
                duration: _duration,
                curve: Curves.easeOutCubic,
                turns: isExpanded ? 0 : -0.25,
                child: const Icon(
                  Icons.keyboard_arrow_down_rounded,
                  size: AppSizes.iconMd,
                  color: AppColors.SIDEBAR_ICON,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
