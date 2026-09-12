import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../models/sidebar_item_model.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/formatters/initials_formatter.dart';
import '../loaders/shimmer_box.dart';

class AppSidebar extends StatelessWidget {
  final List<SidebarItemModel> items;
  final String activeItemId;
  final ValueChanged<String> onItemSelected;
  final bool isCollapsed;
  final VoidCallback? onToggleCollapse;
  final Widget profileCard;
  final VoidCallback? onLogout;

  const AppSidebar({
    super.key,
    required this.items,
    required this.activeItemId,
    required this.onItemSelected,
    required this.profileCard,
    this.isCollapsed = false,
    this.onToggleCollapse,
    this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: OverflowBox(
        alignment: Alignment.topLeft,
        minWidth: _targetWidth,
        maxWidth: _targetWidth,
        child: _buildBody(),
      ),
    );
  }

  double get _targetWidth => isCollapsed
      ? AppSizes.sidebarCollapsedWidth
      : AppSizes.sidebarExpandedWidth;

  Widget _buildBody() {
    return SelectionContainer.disabled(child: _buildChrome());
  }

  Widget _buildChrome() {
    return DecoratedBox(
      decoration: const BoxDecoration(
        color: AppColors.SIDEBAR_BG,
        border: Border(
          right: BorderSide(
            color: AppColors.SIDEBAR_BORDER,
            width: AppSizes.borderThin,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SidebarBrandingSection(isCollapsed: isCollapsed),
          SizedBox(height: isCollapsed ? AppSpacing.smd : AppSpacing.md),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isCollapsed ? AppSpacing.sm : AppSpacing.smd,
            ),
            child: profileCard,
          ),
          const SizedBox(height: AppSpacing.md),
          const SidebarDivider(),
          const SizedBox(height: AppSpacing.md),
          Expanded(
            child: ClipRect(
              child: ListView.separated(
                padding: EdgeInsets.symmetric(
                  horizontal: isCollapsed ? AppSpacing.sm : AppSpacing.smd,
                ),
                itemCount: items.length,
                separatorBuilder: (context, index) =>
                    const SidebarDivider(indent: AppSizes.sidebarDividerIndent),
                itemBuilder: (context, index) {
                  final item = items[index];
                  return SidebarItem(
                    item: item,
                    isActive: activeItemId == item.id,
                    isCollapsed: isCollapsed,
                    onTap: () => onItemSelected(item.id),
                  );
                },
              ),
            ),
          ),
          const SidebarDivider(),
          Padding(
            padding: EdgeInsets.symmetric(
              horizontal: isCollapsed ? AppSpacing.sm : AppSpacing.smd,
              vertical: AppSpacing.smd,
            ),
            child: _buildFooter(),
          ),
        ],
      ),
    );
  }

  Widget _buildFooter() {
    final VoidCallback? toggle = onToggleCollapse;

    if (isCollapsed) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (onLogout != null)
            SidebarLogoutButton(isCollapsed: true, onLogout: onLogout!),
          if (toggle != null) ...[
            const SizedBox(height: AppSpacing.sm),
            SidebarCollapseToggle(isCollapsed: true, onToggleCollapse: toggle),
          ],
        ],
      );
    }

    return Row(
      children: [
        if (onLogout != null)
          Expanded(
            child: SidebarLogoutButton(isCollapsed: false, onLogout: onLogout!),
          ),
        if (toggle != null) ...[
          const SizedBox(width: AppSpacing.sm),
          SidebarCollapseToggle(isCollapsed: false, onToggleCollapse: toggle),
        ],
      ],
    );
  }
}

class SidebarDivider extends StatelessWidget {
  final double indent;

  const SidebarDivider({super.key, this.indent = 0});

  @override
  Widget build(BuildContext context) {
    return Divider(
      color: AppColors.SIDEBAR_DIVIDER,
      height: AppSizes.borderThin,
      thickness: AppSizes.sidebarDividerThickness,
      indent: indent,
      endIndent: indent,
    );
  }
}

class SidebarBrandingSection extends StatelessWidget {
  final bool isCollapsed;

  static const String _logoAsset = 'assets/logo/saiseeds-logo.png';
  static const Duration _duration = Duration(milliseconds: 200);

  const SidebarBrandingSection({super.key, required this.isCollapsed});

  @override
  Widget build(BuildContext context) {
    final double side = isCollapsed
        ? AppSizes.sidebarLogoCollapsed
        : AppSizes.sidebarLogo;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: EdgeInsets.symmetric(
            horizontal: AppSpacing.md,
            vertical: isCollapsed ? AppSpacing.smd : AppSpacing.lgs,
          ),
          child: Center(
            child: AnimatedContainer(
              duration: _duration,
              width: side,
              height: side,
              child: Image.asset(
                _logoAsset,
                fit: BoxFit.contain,
                filterQuality: FilterQuality.medium,
                semanticLabel: AppStrings.LOGIN_LOGO_LABEL,
                errorBuilder: (context, error, stackTrace) => Container(
                  padding: const EdgeInsets.all(AppSpacing.sm),
                  decoration: const BoxDecoration(
                    color: AppColors.PRIMARY,
                    borderRadius: BorderRadius.all(
                      Radius.circular(AppRadius.sm),
                    ),
                  ),
                  child: Icon(
                    Icons.eco_rounded,
                    color: AppColors.TEXT_ON_PRIMARY,
                    size: isCollapsed
                        ? AppSizes.sidebarLogoFallbackIconCollapsed
                        : AppSizes.sidebarLogoFallbackIcon,
                  ),
                ),
              ),
            ),
          ),
        ),
        const SidebarDivider(),
      ],
    );
  }
}

class SidebarCollapseToggle extends StatelessWidget {
  final bool isCollapsed;
  final VoidCallback onToggleCollapse;

  const SidebarCollapseToggle({
    super.key,
    required this.isCollapsed,
    required this.onToggleCollapse,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: isCollapsed
          ? AppStrings.SIDEBAR_EXPAND
          : AppStrings.SIDEBAR_COLLAPSE,
      preferBelow: false,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onToggleCollapse,
          child: SizedBox(
            width: AppSizes.sidebarToggleTile,
            height: AppSizes.sidebarToggleTile,
            child: Icon(
              isCollapsed ? Icons.menu_rounded : Icons.menu_open_rounded,
              size: AppSizes.iconXl,
              color: AppColors.SIDEBAR_ICON,
            ),
          ),
        ),
      ),
    );
  }
}

class SidebarProfileCard extends StatelessWidget {
  final String? name;
  final String? roleLabel;
  final bool isCollapsed;
  final bool isActive;
  final VoidCallback? onTap;

  static const Duration _duration = Duration(milliseconds: 200);

  const SidebarProfileCard({
    super.key,
    this.name,
    this.roleLabel,
    this.isCollapsed = false,
    this.isActive = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    if (name == null) {
      return _SidebarProfilePlaceholder(isCollapsed: isCollapsed);
    }

    final double avatarSize = isCollapsed
        ? AppSizes.sidebarAvatarCollapsed
        : AppSizes.sidebarAvatar;

    final Widget avatar = Container(
      width: avatarSize,
      height: avatarSize,
      alignment: Alignment.center,
      decoration: const BoxDecoration(
        shape: BoxShape.circle,
        color: AppColors.SURFACE,
      ),
      child: Text(
        InitialsFormatter.fromName(name),
        style: AppTypography.labelStrong.copyWith(
          color: AppColors.PRIMARY,
          letterSpacing: 0.2,
        ),
      ),
    );

    final Widget card = AnimatedContainer(
      duration: _duration,
      padding: EdgeInsets.symmetric(
        horizontal: isCollapsed ? AppSpacing.xs : AppSpacing.smd,
        vertical: AppSpacing.sm,
      ),
      decoration: BoxDecoration(
        color: isActive ? AppColors.PRIMARY : AppColors.SIDEBAR_PROFILE_BG,
        borderRadius: const BorderRadius.all(Radius.circular(AppRadius.md)),
      ),
      child: Row(
        mainAxisAlignment: isCollapsed
            ? MainAxisAlignment.center
            : MainAxisAlignment.start,
        children: [
          avatar,
          if (!isCollapsed) ...[
            const SizedBox(width: AppSpacing.smd),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    roleLabel ?? AppStrings.PROFILE_ROLE_UNKNOWN,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.caption.copyWith(
                      color: isActive
                          ? AppColors.SIDEBAR_ON_PRIMARY_MUTED
                          : AppColors.TEXT_SECONDARY,
                      fontWeight: FontWeight.w700,
                      height: 1.2,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.xxs),
                  Text(
                    name!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      color: isActive
                          ? AppColors.TEXT_ON_PRIMARY
                          : AppColors.SIDEBAR_TEXT_ACTIVE,
                      fontWeight: FontWeight.w800,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );

    final Widget tappable = MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(onTap: onTap, child: card),
    );

    if (!isCollapsed) return tappable;

    return Tooltip(message: name!, preferBelow: false, child: tappable);
  }
}

class _SidebarProfilePlaceholder extends StatelessWidget {
  final bool isCollapsed;

  const _SidebarProfilePlaceholder({required this.isCollapsed});

  @override
  Widget build(BuildContext context) {
    final double avatarSize = isCollapsed
        ? AppSizes.sidebarAvatarCollapsed
        : AppSizes.sidebarAvatar;

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCollapsed ? AppSpacing.xs : AppSpacing.smd,
        vertical: AppSpacing.sm,
      ),
      decoration: const BoxDecoration(
        color: AppColors.SIDEBAR_PROFILE_BG,
        borderRadius: BorderRadius.all(Radius.circular(AppRadius.md)),
      ),
      child: Row(
        mainAxisAlignment: isCollapsed
            ? MainAxisAlignment.center
            : MainAxisAlignment.start,
        children: [
          ShimmerBox(
            width: avatarSize,
            height: avatarSize,
            borderRadius: AppRadius.full,
          ),
          if (!isCollapsed) ...[
            const SizedBox(width: AppSpacing.smd),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  ShimmerBox(
                    width: AppSizes.sidebarShimmerLabelWidth,
                    height: AppSizes.sidebarShimmerLabel,
                  ),
                  SizedBox(height: AppSpacing.xs),
                  ShimmerBox(
                    width: AppSizes.sidebarShimmerValueWidth,
                    height: AppSizes.sidebarShimmerValue,
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class SidebarItem extends StatefulWidget {
  final SidebarItemModel item;
  final bool isActive;
  final bool isCollapsed;
  final VoidCallback onTap;

  const SidebarItem({
    super.key,
    required this.item,
    required this.isActive,
    required this.isCollapsed,
    required this.onTap,
  });

  @override
  State<SidebarItem> createState() => _SidebarItemState();
}

class _SidebarItemState extends State<SidebarItem> {
  static const Duration _fillDuration = Duration(milliseconds: 200);
  static const Duration _railDuration = Duration(milliseconds: 250);

  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final Color fill;
    if (widget.isActive) {
      fill = AppColors.SIDEBAR_ITEM_SELECTED;
    } else if (_isHovered) {
      fill = AppColors.SIDEBAR_ITEM_HOVER;
    } else {
      fill = AppColors.TRANSPARENT;
    }

    final Color foreground = widget.isActive
        ? AppColors.SIDEBAR_ICON_ACTIVE
        : (_isHovered ? AppColors.SIDEBAR_TEXT_ACTIVE : AppColors.SIDEBAR_TEXT);

    final Widget tile = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: _fillDuration,
          curve: Curves.easeOutCubic,
          height: AppSizes.sidebarItemHeight,
          margin: const EdgeInsets.symmetric(vertical: AppSpacing.xs),
          decoration: BoxDecoration(
            color: fill,
            borderRadius: const BorderRadius.all(Radius.circular(AppRadius.md)),
          ),
          child: Stack(
            alignment: Alignment.centerLeft,
            children: [
              AnimatedContainer(
                duration: _railDuration,
                curve: Curves.easeOutCubic,
                width: AppSizes.sidebarActiveRail,
                height: widget.isActive ? AppSizes.sidebarActiveRailHeight : 0,
                decoration: const BoxDecoration(
                  color: AppColors.PRIMARY,
                  borderRadius: BorderRadius.all(
                    Radius.circular(AppSizes.sidebarActiveRailRadius),
                  ),
                ),
              ),
              Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: widget.isCollapsed ? 0 : AppSpacing.md,
                ),
                child: Row(
                  mainAxisAlignment: widget.isCollapsed
                      ? MainAxisAlignment.center
                      : MainAxisAlignment.start,
                  children: [
                    TweenAnimationBuilder<Color?>(
                      duration: _fillDuration,
                      curve: Curves.easeOutCubic,
                      tween: ColorTween(
                        end: widget.isActive
                            ? AppColors.SIDEBAR_ICON_ACTIVE
                            : (_isHovered
                                  ? AppColors.SIDEBAR_TEXT_ACTIVE
                                  : AppColors.SIDEBAR_ICON),
                      ),
                      builder: (context, color, child) => Icon(
                        widget.item.icon,
                        size: AppSizes.iconLg,
                        color: color,
                      ),
                    ),
                    if (!widget.isCollapsed) ...[
                      const SizedBox(width: AppSpacing.smd),
                      Expanded(
                        child: AnimatedDefaultTextStyle(
                          duration: _fillDuration,
                          curve: Curves.easeOutCubic,
                          style: AppTypography.bodyMedium.copyWith(
                            color: foreground,
                            fontWeight: widget.isActive
                                ? FontWeight.w600
                                : FontWeight.w500,
                          ),
                          child: Text(
                            widget.item.label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (!widget.isCollapsed) return tile;

    return Tooltip(
      message: widget.item.label,
      preferBelow: false,
      verticalOffset: AppSizes.sidebarTooltipOffset,
      child: tile,
    );
  }
}

class SidebarLogoutButton extends StatelessWidget {
  final bool isCollapsed;
  final VoidCallback onLogout;

  const SidebarLogoutButton({
    super.key,
    required this.isCollapsed,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    final Widget button = MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onLogout,
        child: Container(
          height: AppSizes.sidebarLogoutHeight,
          padding: EdgeInsets.symmetric(
            horizontal: isCollapsed ? 0 : AppSpacing.md,
          ),
          decoration: const BoxDecoration(
            color: AppColors.PRIMARY,
            borderRadius: BorderRadius.all(Radius.circular(AppRadius.md)),
          ),
          child: Row(
            mainAxisAlignment: isCollapsed
                ? MainAxisAlignment.center
                : MainAxisAlignment.start,
            children: [
              const Icon(
                Icons.logout_rounded,
                size: AppSizes.iconLg,
                color: AppColors.TEXT_ON_PRIMARY,
              ),
              if (!isCollapsed) ...[
                const SizedBox(width: AppSpacing.smd),
                Expanded(
                  child: Text(
                    AppStrings.LOGOUT,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.bodyMedium.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.TEXT_ON_PRIMARY,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );

    if (!isCollapsed) return button;

    return Tooltip(
      message: AppStrings.LOGOUT,
      preferBelow: false,
      child: button,
    );
  }
}
