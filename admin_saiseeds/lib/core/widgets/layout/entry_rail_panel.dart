import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class EntryRailItem {
  final String title;
  final bool isPrimary;

  const EntryRailItem({required this.title, this.isPrimary = false});
}

class EntryRailPanel extends StatelessWidget {
  final String hint;
  final List<EntryRailItem> entries;
  final int selectedIndex;
  final ValueChanged<int> onSelected;
  final Widget detail;
  final String addLabel;
  final String primaryLabel;
  final VoidCallback? onAdd;
  final ValueChanged<int>? onRemove;

  const EntryRailPanel({
    super.key,
    required this.hint,
    required this.entries,
    required this.selectedIndex,
    required this.onSelected,
    required this.detail,
    required this.addLabel,
    required this.primaryLabel,
    this.onAdd,
    this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: const BoxDecoration(color: AppColors.SURFACE),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: AppSizes.entryRailWidth,
            child: DecoratedBox(
              decoration: const BoxDecoration(
                color: AppColors.SIDEBAR_BG,
                border: Border(right: BorderSide(color: AppColors.DIVIDER)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _buildHint(),
                  Expanded(child: _buildList()),
                  if (onAdd != null) _buildAddAction(),
                ],
              ),
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(AppSpacing.lg),
              child: detail,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHint() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: const BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        border: Border(bottom: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.info_outline_rounded,
            size: AppSizes.iconSm,
            color: AppColors.TEXT_SECONDARY,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Text(
              hint,
              style: AppTypography.labelSmall,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildList() {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          for (int index = 0; index < entries.length; index++)
            _EntryRailTile(
              entry: entries[index],
              index: index,
              isSelected: index == selectedIndex,
              primaryLabel: primaryLabel,
              onTap: () => onSelected(index),
              onRemove: onRemove == null ? null : () => onRemove!(index),
            ),
        ],
      ),
    );
  }

  Widget _buildAddAction() {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.smd),
      decoration: const BoxDecoration(
        color: AppColors.SURFACE,
        border: Border(top: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: _EntryRailAddButton(label: addLabel, onPressed: onAdd!),
    );
  }
}

class _EntryRailTile extends StatelessWidget {
  final EntryRailItem entry;
  final int index;
  final bool isSelected;
  final String primaryLabel;
  final VoidCallback onTap;
  final VoidCallback? onRemove;

  static const Duration _duration = Duration(milliseconds: 250);

  const _EntryRailTile({
    required this.entry,
    required this.index,
    required this.isSelected,
    required this.primaryLabel,
    required this.onTap,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: _duration,
          curve: Curves.easeOutCubic,
          color: isSelected
              ? AppColors.SIDEBAR_ITEM_SELECTED
              : AppColors.TRANSPARENT,
          child: Stack(
            children: [
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                width: AppSizes.entryRailIndicator,
                child: Center(
                  child: AnimatedContainer(
                    duration: _duration,
                    curve: Curves.easeOutCubic,
                    width: AppSizes.entryRailIndicator,
                    height: isSelected
                        ? AppSizes.entryRailIndicatorHeight
                        : 0,
                    decoration: const BoxDecoration(
                      color: AppColors.PRIMARY,
                      borderRadius: BorderRadius.all(
                        Radius.circular(AppSizes.entryRailIndicatorRadius),
                      ),
                    ),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.md,
                  vertical: AppSizes.entryRailItemVertical,
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            entry.title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: AppTypography.labelMedium.copyWith(
                              color: isSelected
                                  ? AppColors.PRIMARY
                                  : AppColors.TEXT_PRIMARY,
                              fontWeight: isSelected
                                  ? FontWeight.w800
                                  : FontWeight.w600,
                            ),
                          ),
                          if (entry.isPrimary) ...[
                            const SizedBox(height: AppSpacing.xxs),
                            Text(
                              primaryLabel,
                              style: AppTypography.labelSmall.copyWith(
                                color: AppColors.SUCCESS,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (onRemove != null) ...[
                      const SizedBox(width: AppSpacing.sm),
                      _EntryRailRemoveButton(
                        isSelected: isSelected,
                        onPressed: onRemove!,
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
  }
}

class _EntryRailRemoveButton extends StatelessWidget {
  final bool isSelected;
  final VoidCallback onPressed;

  const _EntryRailRemoveButton({
    required this.isSelected,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onPressed,
        child: Icon(
          Icons.delete_outline_rounded,
          size: AppSizes.iconSm,
          color: isSelected ? AppColors.ERROR : AppColors.TEXT_DISABLED,
        ),
      ),
    );
  }
}

class _EntryRailAddButton extends StatefulWidget {
  final String label;
  final VoidCallback onPressed;

  const _EntryRailAddButton({required this.label, required this.onPressed});

  @override
  State<_EntryRailAddButton> createState() => _EntryRailAddButtonState();
}

class _EntryRailAddButtonState extends State<_EntryRailAddButton> {
  static const Duration _duration = Duration(milliseconds: 160);
  static const double _hoverOpacity = 0.08;

  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: _duration,
          curve: Curves.easeOutCubic,
          height: AppSizes.entryRailAddHeight,
          decoration: BoxDecoration(
            color: _isHovered
                ? AppColors.PRIMARY.withValues(alpha: _hoverOpacity)
                : AppColors.TRANSPARENT,
            border: Border.all(
              color: AppColors.PRIMARY,
              width: AppSizes.borderMedium,
            ),
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          alignment: Alignment.center,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.add_rounded,
                size: AppSizes.iconMd,
                color: AppColors.PRIMARY,
              ),
              const SizedBox(width: AppSpacing.xs),
              Flexible(
                child: Text(
                  widget.label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.button.copyWith(
                    color: AppColors.PRIMARY,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
