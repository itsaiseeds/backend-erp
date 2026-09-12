import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../bloc/clients_cubit.dart';

class ClientsViewSwitcher extends StatelessWidget {
  final ClientsViewMode selected;
  final int pendingCount;
  final ValueChanged<ClientsViewMode> onChanged;

  const ClientsViewSwitcher({
    super.key,
    required this.selected,
    required this.onChanged,
    this.pendingCount = 0,
  });

  static const Duration _duration = Duration(milliseconds: 220);
  static const Curve _curve = Curves.easeOutCubic;

  static const List<ClientsViewMode> _views = [
    ClientsViewMode.verified,
    ClientsViewMode.pending,
  ];

  static String _labelFor(ClientsViewMode view) {
    switch (view) {
      case ClientsViewMode.pending:
        return AppStrings.CLIENTS_VIEW_PENDING;
      case ClientsViewMode.verified:
        return AppStrings.CLIENTS_VIEW_VERIFIED;
    }
  }

  static IconData _iconFor(ClientsViewMode view) {
    switch (view) {
      case ClientsViewMode.pending:
        return Icons.pending_actions_outlined;
      case ClientsViewMode.verified:
        return Icons.verified_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final int selectedIndex = _views.indexOf(selected);

    return Container(
      height: AppSizes.clientSwitcherHeight,
      padding: const EdgeInsets.all(AppSpacing.xxs),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        border: Border.all(color: AppColors.BORDER),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final double segmentWidth = constraints.maxWidth / _views.length;

          return Stack(
            children: [
              AnimatedPositioned(
                duration: _duration,
                curve: _curve,
                left: segmentWidth * selectedIndex,
                top: 0,
                bottom: 0,
                width: segmentWidth,
                child: Container(
                  decoration: BoxDecoration(
                    color: AppColors.SURFACE,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.BORDER),
                  ),
                ),
              ),
              Row(
                children: _views.map((view) {
                  final bool isSelected = view == selected;

                  return Expanded(
                    child: _Segment(
                      label: _labelFor(view),
                      icon: _iconFor(view),
                      isSelected: isSelected,
                      badgeCount: view == ClientsViewMode.pending
                          ? pendingCount
                          : 0,
                      duration: _duration,
                      curve: _curve,
                      onTap: () => onChanged(view),
                    ),
                  );
                }).toList(),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Segment extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isSelected;
  final int badgeCount;
  final Duration duration;
  final Curve curve;
  final VoidCallback onTap;

  const _Segment({
    required this.label,
    required this.icon,
    required this.isSelected,
    required this.badgeCount,
    required this.duration,
    required this.curve,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final Color foreground = isSelected
        ? AppColors.PRIMARY
        : AppColors.TEXT_SECONDARY;

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Center(
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: AppSizes.iconSm, color: foreground),
              const SizedBox(width: AppSpacing.sm),
              Flexible(
                child: AnimatedDefaultTextStyle(
                  duration: duration,
                  curve: curve,
                  style: isSelected
                      ? AppTypography.labelMedium.copyWith(color: foreground)
                      : AppTypography.bodySmall,
                  child: Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              if (badgeCount > 0) ...[
                const SizedBox(width: AppSpacing.sm),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.sm,
                    vertical: AppSpacing.xxs,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? AppColors.PRIMARY
                        : AppColors.BORDER_STRONG,
                    borderRadius: BorderRadius.circular(AppRadius.full),
                  ),
                  child: Text(
                    '$badgeCount',
                    style: AppTypography.labelSmall.copyWith(
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
  }
}
