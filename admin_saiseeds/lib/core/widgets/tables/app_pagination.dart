import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppPagination extends StatelessWidget {
  final int currentPage;
  final int totalPages;
  final ValueChanged<int> onPageChanged;

  const AppPagination({
    super.key,
    required this.currentPage,
    required this.totalPages,
    required this.onPageChanged,
  });

  List<int> _visiblePages() {
    if (totalPages <= 5) {
      return List.generate(totalPages, (i) => i + 1);
    }
    int start = (currentPage - 2).clamp(1, totalPages - 4);
    return List.generate(5, (i) => start + i);
  }

  @override
  Widget build(BuildContext context) {
    if (totalPages <= 0) return const SizedBox.shrink();

    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        _NavButton(
          icon: Icons.chevron_left_rounded,
          onTap: currentPage > 1 ? () => onPageChanged(currentPage - 1) : null,
        ),
        const SizedBox(width: AppSpacing.xs),
        for (final page in _visiblePages()) ...[
          _PageButton(
            page: page,
            isActive: page == currentPage,
            onTap: () => onPageChanged(page),
          ),
          const SizedBox(width: AppSpacing.xs),
        ],
        _NavButton(
          icon: Icons.chevron_right_rounded,
          onTap: currentPage < totalPages
              ? () => onPageChanged(currentPage + 1)
              : null,
        ),
      ],
    );
  }
}

class _PageButton extends StatelessWidget {
  final int page;
  final bool isActive;
  final VoidCallback onTap;

  const _PageButton({
    required this.page,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Container(
          width: AppSpacing.xl,
          height: AppSpacing.xl,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: isActive ? AppColors.PRIMARY : AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            border: Border.all(
              color: isActive ? AppColors.PRIMARY : AppColors.BORDER,
            ),
          ),
          child: Text(
            '$page',
            style: AppTypography.bodySmall.copyWith(
              color: isActive ? AppColors.TEXT_ON_PRIMARY : AppColors.TEXT_PRIMARY,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

class _NavButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback? onTap;

  const _NavButton({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = onTap == null;
    return MouseRegion(
      cursor: isDisabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppRadius.sm),
        child: Container(
          width: AppSpacing.xl,
          height: AppSpacing.xl,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.sm),
            border: Border.all(color: AppColors.BORDER),
          ),
          child: Icon(
            icon,
            size: AppSpacing.md,
            color: isDisabled ? AppColors.TEXT_DISABLED : AppColors.TEXT_PRIMARY,
          ),
        ),
      ),
    );
  }
}
