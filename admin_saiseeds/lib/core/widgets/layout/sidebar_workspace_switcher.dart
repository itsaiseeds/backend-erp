import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../constants/font_sizes.dart';
import '../../models/sidebar_workspace_model.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

/// Switches the sidebar between the two halves of the app.
///
/// Expanded this is a segmented control: with only two choices, showing both
/// costs one row and makes switching a single click instead of open-then-pick.
/// The collapsed rail has no room for labels, so it falls back to a menu.
class SidebarWorkspaceSwitcher extends StatelessWidget {
  final List<ResolvedSidebarWorkspace> workspaces;
  final String activeWorkspaceId;
  final bool isCollapsed;
  final ValueChanged<String> onWorkspaceSelected;

  const SidebarWorkspaceSwitcher({
    super.key,
    required this.workspaces,
    required this.activeWorkspaceId,
    required this.isCollapsed,
    required this.onWorkspaceSelected,
  });

  @override
  Widget build(BuildContext context) {
    if (workspaces.length < 2) return const SizedBox.shrink();
    if (isCollapsed) return _buildRailMenu();

    final int activeIndex = workspaces.indexWhere(
      (entry) => entry.id == activeWorkspaceId,
    );
    final int selected = activeIndex < 0 ? 0 : activeIndex;

    // One thumb slides between the segments rather than each segment fading
    // its own fill, so the selection reads as a single moving object.
    final double alignX = workspaces.length == 1
        ? -1
        : (selected / (workspaces.length - 1)) * 2 - 1;

    return Container(
      padding: const EdgeInsets.all(AppSpacing.xxs),
      decoration: BoxDecoration(
        color: AppColors.SIDEBAR_ACTIVE_BG,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: SizedBox(
        height: AppSizes.sidebarWorkspaceSegmentHeight,
        child: Stack(
          children: [
            AnimatedAlign(
              duration: _slideDuration,
              curve: Curves.easeOutCubic,
              alignment: Alignment(alignX, 0),
              child: FractionallySizedBox(
                widthFactor: 1 / workspaces.length,
                heightFactor: 1,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: AppColors.SURFACE,
                    borderRadius: BorderRadius.circular(AppRadius.sm),
                    border: Border.all(
                      color: AppColors.BORDER,
                      width: AppSizes.borderThin,
                    ),
                  ),
                ),
              ),
            ),
            Row(
              children: [
                for (final ResolvedSidebarWorkspace entry in workspaces)
                  Expanded(
                    child: _SwitcherSegment(
                      workspace: entry.workspace,
                      isActive: entry.id == activeWorkspaceId,
                      onTap: () => onWorkspaceSelected(entry.id),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  static const Duration _slideDuration = Duration(milliseconds: 260);

  Widget _buildRailMenu() {
    final ResolvedSidebarWorkspace active = workspaces.firstWhere(
      (entry) => entry.id == activeWorkspaceId,
      orElse: () => workspaces.first,
    );

    return Tooltip(
      message: '${AppStrings.WORKSPACE_SWITCH_LABEL}: ${active.workspace.label}',
      preferBelow: false,
      child: PopupMenuButton<String>(
        tooltip: '',
        position: PopupMenuPosition.under,
        onSelected: onWorkspaceSelected,
        itemBuilder: (context) => [
          for (final ResolvedSidebarWorkspace entry in workspaces)
            PopupMenuItem<String>(
              value: entry.id,
              child: Row(
                children: [
                  Icon(
                    entry.workspace.icon,
                    size: AppSizes.iconMd,
                    color: entry.id == activeWorkspaceId
                        ? AppColors.SIDEBAR_ICON_ACTIVE
                        : AppColors.SIDEBAR_ICON,
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text(entry.workspace.label, style: AppTypography.bodyMedium),
                ],
              ),
            ),
        ],
        child: Container(
          height: AppSizes.sidebarItemHeight,
          decoration: BoxDecoration(
            color: AppColors.SIDEBAR_ACTIVE_BG,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: Icon(
            active.workspace.icon,
            size: AppSizes.iconLg,
            color: AppColors.SIDEBAR_ICON_ACTIVE,
          ),
        ),
      ),
    );
  }
}

class _SwitcherSegment extends StatelessWidget {
  final SidebarWorkspaceModel workspace;
  final bool isActive;
  final VoidCallback onTap;

  static const Duration _duration = Duration(milliseconds: 180);

  const _SwitcherSegment({
    required this.workspace,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: workspace.hint,
      preferBelow: false,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          child: SizedBox(
            height: AppSizes.sidebarWorkspaceSegmentHeight,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                TweenAnimationBuilder<Color?>(
                  duration: _duration,
                  curve: Curves.easeOutCubic,
                  tween: ColorTween(
                    end: isActive
                        ? AppColors.SIDEBAR_ICON_ACTIVE
                        : AppColors.SIDEBAR_ICON,
                  ),
                  builder: (context, color, child) =>
                      Icon(workspace.icon, size: AppSizes.iconSm, color: color),
                ),
                const SizedBox(width: AppSpacing.xs),
                Flexible(
                  child: AnimatedDefaultTextStyle(
                    duration: _duration,
                    curve: Curves.easeOutCubic,
                    style: AppTypography.bodyMedium.copyWith(
                      fontSize: AppFontSizes.FONT_13,
                      fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                      color: isActive
                          ? AppColors.SIDEBAR_TEXT_ACTIVE
                          : AppColors.SIDEBAR_TEXT,
                    ),
                    child: Text(
                      workspace.label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
