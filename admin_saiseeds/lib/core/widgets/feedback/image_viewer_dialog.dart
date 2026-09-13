import 'package:flutter/material.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class ImageViewerDialog extends StatefulWidget {
  final String url;
  final String title;

  const ImageViewerDialog({super.key, required this.url, this.title = ''});

  static Future<void> show(
    BuildContext context, {
    required String url,
    String title = '',
  }) {
    return showDialog<void>(
      context: context,
      barrierColor: AppColors.OVERLAY_STRONG,
      builder: (_) => ImageViewerDialog(url: url, title: title),
    );
  }

  @override
  State<ImageViewerDialog> createState() => _ImageViewerDialogState();
}

class _ImageViewerDialogState extends State<ImageViewerDialog> {
  static const double _minScale = 1.0;
  static const double _maxScale = 5.0;
  static const double _scaleStep = 0.5;
  static const Duration _duration = Duration(milliseconds: 200);

  final TransformationController _controller = TransformationController();

  double _scale = _minScale;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _applyScale(double next) {
    final double clamped = next.clamp(_minScale, _maxScale);
    setState(() {
      _scale = clamped;
      _controller.value = Matrix4.identity()..scaleByDouble(
        clamped,
        clamped,
        clamped,
        1,
      );
    });
  }

  void _zoomIn() => _applyScale(_scale + _scaleStep);

  void _zoomOut() => _applyScale(_scale - _scaleStep);

  void _reset() => _applyScale(_minScale);

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: AppColors.TRANSPARENT,
      insetPadding: const EdgeInsets.all(AppSpacing.xl),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  widget.title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.titleMedium.copyWith(
                    color: AppColors.TEXT_ON_PRIMARY,
                  ),
                ),
              ),
              _ViewerButton(
                icon: Icons.close_rounded,
                tooltip: AppStrings.CLOSE,
                onTap: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.smd),
          Flexible(
            child: Container(
              decoration: BoxDecoration(
                color: AppColors.SURFACE,
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              clipBehavior: Clip.antiAlias,
              child: InteractiveViewer(
                transformationController: _controller,
                minScale: _minScale,
                maxScale: _maxScale,
                onInteractionEnd: (_) {
                  final double current =
                      _controller.value.getMaxScaleOnAxis();
                  if (current != _scale) setState(() => _scale = current);
                },
                child: Center(
                  child: Image.network(
                    widget.url,
                    fit: BoxFit.contain,
                    errorBuilder: (context, error, stack) => Padding(
                      padding: const EdgeInsets.all(AppSpacing.xl),
                      child: Text(
                        AppStrings.IMAGE_LOAD_FAILED,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.TEXT_SECONDARY,
                        ),
                      ),
                    ),
                    loadingBuilder: (context, child, progress) {
                      if (progress == null) return child;
                      return const Padding(
                        padding: EdgeInsets.all(AppSpacing.xl),
                        child: SizedBox(
                          width: AppSizes.iconXl,
                          height: AppSizes.iconXl,
                          child: CircularProgressIndicator(
                            strokeWidth: AppSizes.borderMedium,
                            color: AppColors.PRIMARY,
                          ),
                        ),
                      );
                    },
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.smd),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _ViewerButton(
                icon: Icons.remove_rounded,
                tooltip: AppStrings.IMAGE_ZOOM_OUT,
                onTap: _scale <= _minScale ? null : _zoomOut,
              ),
              const SizedBox(width: AppSpacing.smd),
              AnimatedSwitcher(
                duration: _duration,
                child: Text(
                  '${(_scale * 100).round()}%',
                  key: ValueKey<int>((_scale * 100).round()),
                  style: AppTypography.labelMedium.copyWith(
                    color: AppColors.TEXT_ON_PRIMARY,
                  ),
                ),
              ),
              const SizedBox(width: AppSpacing.smd),
              _ViewerButton(
                icon: Icons.add_rounded,
                tooltip: AppStrings.IMAGE_ZOOM_IN,
                onTap: _scale >= _maxScale ? null : _zoomIn,
              ),
              const SizedBox(width: AppSpacing.md),
              _ViewerButton(
                icon: Icons.restart_alt_rounded,
                tooltip: AppStrings.IMAGE_RESET,
                onTap: _scale == _minScale ? null : _reset,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ViewerButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback? onTap;

  const _ViewerButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isDisabled = onTap == null;

    return Tooltip(
      message: tooltip,
      child: MouseRegion(
        cursor: isDisabled
            ? SystemMouseCursors.basic
            : SystemMouseCursors.click,
        child: GestureDetector(
          onTap: onTap,
          child: Container(
            width: AppSizes.imageViewerButton,
            height: AppSizes.imageViewerButton,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.SURFACE,
              shape: BoxShape.circle,
              border: Border.all(color: AppColors.BORDER),
            ),
            child: Icon(
              icon,
              size: AppSizes.iconMd,
              color: isDisabled
                  ? AppColors.TEXT_DISABLED
                  : AppColors.TEXT_PRIMARY,
            ),
          ),
        ),
      ),
    );
  }
}
