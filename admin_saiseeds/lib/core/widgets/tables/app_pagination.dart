import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class AppPagination extends StatelessWidget {
  static const String ELLIPSIS = '...';

  final int currentPage;
  final int totalPages;
  final int? totalItems;
  final int? itemsPerPage;
  final ValueChanged<int> onPageChanged;
  final bool hideWhenSinglePage;

  const AppPagination({
    super.key,
    required this.currentPage,
    required this.totalPages,
    this.totalItems,
    this.itemsPerPage,
    required this.onPageChanged,
    this.hideWhenSinglePage = false,
  });

  @override
  Widget build(BuildContext context) {
    if (totalPages < 1) return const SizedBox.shrink();
    if (hideWhenSinglePage && totalPages <= 1) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(
        vertical: AppSpacing.sm,
        horizontal: AppSpacing.smd,
      ),
      decoration: const BoxDecoration(
        color: AppColors.SURFACE,
        border: Border(top: BorderSide(color: AppColors.DIVIDER)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          _NavButton(
            icon: Icons.chevron_left_rounded,
            onTap: currentPage > 1
                ? () => onPageChanged(currentPage - 1)
                : null,
          ),
          const SizedBox(width: AppSpacing.sm),
          for (final entry in _calculatePages())
            if (entry == ELLIPSIS)
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: AppSpacing.sm),
                child: _EllipsisLabel(),
              )
            else
              _PageButton(
                page: entry as int,
                isActive: entry == currentPage,
                onTap: () => onPageChanged(entry),
              ),
          const SizedBox(width: AppSpacing.sm),
          _NavButton(
            icon: Icons.chevron_right_rounded,
            onTap: currentPage < totalPages
                ? () => onPageChanged(currentPage + 1)
                : null,
          ),
        ],
      ),
    );
  }

  List<Object> _calculatePages() {
    if (totalPages <= 5) {
      return List<Object>.generate(totalPages, (i) => i + 1);
    }

    final List<Object> pages = <Object>[1];

    if (currentPage <= 3) {
      pages.addAll(<Object>[2, 3, 4, ELLIPSIS]);
    } else if (currentPage >= totalPages - 2) {
      pages.addAll(<Object>[
        ELLIPSIS,
        totalPages - 3,
        totalPages - 2,
        totalPages - 1,
      ]);
    } else {
      pages.addAll(<Object>[
        ELLIPSIS,
        currentPage - 1,
        currentPage,
        currentPage + 1,
        ELLIPSIS,
      ]);
    }

    pages.add(totalPages);

    final List<Object> unique = <Object>[];
    for (final page in pages) {
      if (unique.isEmpty || unique.last != page) unique.add(page);
    }
    return unique;
  }
}

class _EllipsisLabel extends StatelessWidget {
  const _EllipsisLabel();

  @override
  Widget build(BuildContext context) {
    return Text(
      AppPagination.ELLIPSIS,
      style: AppTypography.labelMedium.copyWith(
        color: AppColors.TEXT_SECONDARY,
      ),
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
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.smd,
            vertical: AppSpacing.sm,
          ),
          decoration: BoxDecoration(
            color: isActive ? AppColors.PRIMARY : AppColors.SURFACE_VARIANT,
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(
              color: isActive ? AppColors.PRIMARY : AppColors.BORDER,
            ),
          ),
          child: Text(
            '$page',
            style: AppTypography.labelMedium.copyWith(
              color: isActive
                  ? AppColors.TEXT_ON_PRIMARY
                  : AppColors.TEXT_PRIMARY,
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
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(AppSpacing.xs),
          decoration: BoxDecoration(
            color: isDisabled ? AppColors.SURFACE_VARIANT : AppColors.SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.xs),
            border: Border.all(color: AppColors.BORDER),
          ),
          child: Icon(
            icon,
            size: AppSizes.iconLg,
            color: isDisabled
                ? AppColors.TEXT_DISABLED
                : AppColors.TEXT_PRIMARY,
          ),
        ),
      ),
    );
  }
}
