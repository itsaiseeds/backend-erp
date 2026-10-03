import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/layout/app_surface_card.dart';
import '../../data/exports_repository.dart';
import '../../data/models/export_kind.dart';
import '../bloc/exports_cubit.dart';
import '../widgets/export_range_dialog.dart';

class ExportsView extends StatelessWidget {
  const ExportsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<ExportsCubit>(
      create: (context) =>
          ExportsCubit(repository: ExportsRepository(apiClient: apiClient)),
      child: const _ExportsContent(),
    );
  }
}

class _ExportsContent extends StatelessWidget {
  const _ExportsContent();

  /// Cards reflow into as many columns as fit rather than stretching: a
  /// report tile reads badly when it spans a desktop window.
  static const double _minCardWidth = 300;
  static const double _maxContentWidth = 1180;

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ExportsCubit, ExportsState>(
      builder: (context, state) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: _maxContentWidth),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const _Header(),
                  const SizedBox(height: AppSpacing.lg),
                  _buildGrid(context, state),
                  const SizedBox(height: AppSpacing.lg),
                  const _Hints(),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildGrid(BuildContext context, ExportsState state) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final int columns = (constraints.maxWidth / _minCardWidth)
            .floor()
            .clamp(1, 3);
        final double gaps = AppSpacing.md * (columns - 1);
        final double width = (constraints.maxWidth - gaps) / columns;

        return Wrap(
          spacing: AppSpacing.md,
          runSpacing: AppSpacing.md,
          children: [
            for (final ExportKind kind in ExportKind.values)
              SizedBox(
                width: width,
                child: _ExportCard(
                  kind: kind,
                  isBusy: state.isBusyFor(kind),
                  isDisabled: state.isBusy && !state.isBusyFor(kind),
                  onTap: () => ExportRangeDialog.show(
                    context,
                    cubit: context.read<ExportsCubit>(),
                    kind: kind,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _Header extends StatelessWidget {
  const _Header();

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          width: AppSizes.exportHeaderTile,
          height: AppSizes.exportHeaderTile,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.PRIMARY_SURFACE,
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          child: const Icon(
            Icons.download_outlined,
            size: AppSizes.iconXl,
            color: AppColors.PRIMARY,
          ),
        ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(AppStrings.EXPORTS, style: AppTypography.headingSmall),
              const SizedBox(height: AppSpacing.xxs),
              Text(
                AppStrings.EXPORT_SUBTITLE,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _Hints extends StatelessWidget {
  const _Hints();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.SURFACE_VARIANT,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.BORDER),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              const Icon(
                Icons.lightbulb_outline_rounded,
                size: AppSizes.iconSm,
                color: AppColors.TEXT_SECONDARY,
              ),
              const SizedBox(width: AppSpacing.sm),
              Text(
                AppStrings.EXPORT_HINT_TITLE,
                style: AppTypography.labelStrong.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.sm),
          for (final String hint in const [
            AppStrings.EXPORT_HINT_WINDOW,
            AppStrings.EXPORT_HINT_ROWS,
            AppStrings.EXPORT_HINT_HISTORY,
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xxs),
              child: Text(
                '·  $hint',
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _ExportCard extends StatefulWidget {
  final ExportKind kind;
  final bool isBusy;
  final bool isDisabled;
  final VoidCallback onTap;

  const _ExportCard({
    required this.kind,
    required this.isBusy,
    required this.isDisabled,
    required this.onTap,
  });

  @override
  State<_ExportCard> createState() => _ExportCardState();
}

class _ExportCardState extends State<_ExportCard> {
  static const Duration _duration = Duration(milliseconds: 160);

  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final bool isInteractive = !widget.isBusy && !widget.isDisabled;
    final bool isHot = _isHovered && isInteractive;

    return MouseRegion(
      cursor: isInteractive
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: isInteractive ? widget.onTap : null,
        child: Opacity(
          opacity: widget.isDisabled ? 0.45 : 1,
          child: AnimatedContainer(
            duration: _duration,
            curve: Curves.easeOutCubic,
            decoration: BoxDecoration(
              color: AppColors.SURFACE,
              border: Border.all(
                color: isHot ? AppColors.PRIMARY : AppColors.BORDER,
                width: isHot ? AppSizes.borderMedium : AppSizes.borderThin,
              ),
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: AppSurfaceCard(
              child: Padding(
                padding: const EdgeInsets.all(AppSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: AppSizes.exportIconTile,
                          height: AppSizes.exportIconTile,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: AppColors.PRIMARY_SURFACE,
                            borderRadius: BorderRadius.circular(AppRadius.sm),
                          ),
                          child: Icon(
                            widget.kind.icon,
                            size: AppSizes.iconLg,
                            color: AppColors.PRIMARY,
                          ),
                        ),
                        const SizedBox(width: AppSpacing.smd),
                        Expanded(
                          child: Text(
                            widget.kind.label,
                            style: AppTypography.labelStrong,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: AppSpacing.sm),
                    Text(
                      widget.kind.description,
                      style: AppTypography.bodySmall.copyWith(
                        color: AppColors.TEXT_SECONDARY,
                      ),
                    ),
                    const SizedBox(height: AppSpacing.md),
                    _buildAction(isHot),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAction(bool isHot) {
    if (widget.isBusy) {
      return Row(
        children: [
          const SizedBox(
            width: AppSizes.iconSm,
            height: AppSizes.iconSm,
            child: CircularProgressIndicator(
              strokeWidth: AppSizes.borderMedium,
              color: AppColors.PRIMARY,
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          Text(
            AppStrings.EXPORT_BUILDING,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.PRIMARY_DARK,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );
    }

    final Color tone = isHot ? AppColors.PRIMARY : AppColors.TEXT_SECONDARY;

    return Row(
      children: [
        Icon(Icons.event_outlined, size: AppSizes.iconSm, color: tone),
        const SizedBox(width: AppSpacing.sm),
        Text(
          AppStrings.EXPORT_CARD_ACTION,
          style: AppTypography.bodySmall.copyWith(
            color: tone,
            fontWeight: FontWeight.w600,
          ),
        ),
        const Spacer(),
        Icon(Icons.download_outlined, size: AppSizes.iconSm, color: tone),
      ],
    );
  }
}
