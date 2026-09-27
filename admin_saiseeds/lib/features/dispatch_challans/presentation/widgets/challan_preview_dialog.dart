import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:printing/printing.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../data/models/dispatch_challan_model.dart';
import '../../utils/challan_generator.dart';

/// Renders the challan on screen so it can be checked before downloading.
class ChallanPreviewDialog extends StatefulWidget {
  final DispatchChallanModel challan;

  const ChallanPreviewDialog({super.key, required this.challan});

  static Future<void> show(
    BuildContext context,
    DispatchChallanModel challan,
  ) {
    return showDialog<void>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (_) => ChallanPreviewDialog(challan: challan),
    );
  }

  @override
  State<ChallanPreviewDialog> createState() => _ChallanPreviewDialogState();
}

class _ChallanPreviewDialogState extends State<ChallanPreviewDialog> {
  Future<Uint8List>? _pdf;
  bool _isDownloading = false;

  String get _fileName =>
      '${AppStrings.CHALLAN_FILE_PREFIX}'
      '${widget.challan.dispatchPublicId}.pdf';

  // Built once and reused, so previewing then downloading does not lay the
  // document out twice.
  Future<Uint8List> _buildPdf() =>
      _pdf ??= ChallanGenerator.generate(widget.challan);

  Future<void> _download() async {
    setState(() => _isDownloading = true);

    try {
      final Uint8List bytes = await _buildPdf();
      if (!mounted) return;
      await Printing.sharePdf(bytes: bytes, filename: _fileName);
    } catch (_) {
      if (!mounted) return;
      ToastUtils.showError(context, AppStrings.CHALLAN_DOWNLOAD_FAILED);
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);

    return Dialog(
      backgroundColor: AppColors.BACKGROUND,
      insetPadding: const EdgeInsets.all(AppSpacing.xl),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.dialog),
      ),
      child: SizedBox(
        width: viewport.width * 0.72,
        height: viewport.height * 0.9,
        child: Column(
          children: [_buildHeader(), Expanded(child: _buildPreview())],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      color: AppColors.PRIMARY,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.smd,
      ),
      child: Row(
        children: [
          const Icon(
            Icons.local_shipping_outlined,
            size: AppSizes.iconLg,
            color: AppColors.TEXT_ON_PRIMARY,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.CHALLAN_PREVIEW_TITLE,
                  style: AppTypography.headingSmall.copyWith(
                    color: AppColors.TEXT_ON_PRIMARY,
                  ),
                ),
                Text(
                  widget.challan.dispatchPublicId,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.SIDEBAR_ON_PRIMARY_MUTED,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          PrimaryButton(
            label: AppStrings.DOWNLOAD,
            icon: Icons.download_outlined,
            isLoading: _isDownloading,
            onPressed: _isDownloading ? null : _download,
          ),
          const SizedBox(width: AppSpacing.sm),
          // Plain white: the shared IconActionButton paints itself in theme
          // green, which disappears against this header.
          IconButton(
            icon: const Icon(Icons.close_rounded),
            color: AppColors.TEXT_ON_PRIMARY,
            iconSize: AppSizes.iconLg,
            tooltip: AppStrings.CANCEL,
            splashRadius: AppSizes.iconLg,
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _buildPreview() {
    return PdfPreview(
      build: (format) => _buildPdf(),
      pdfFileName: _fileName,
      canChangeOrientation: false,
      canChangePageFormat: false,
      canDebug: false,
      allowPrinting: false,
      allowSharing: false,
      useActions: false,
      loadingWidget: const Center(
        child: CircularProgressIndicator(color: AppColors.PRIMARY),
      ),
    );
  }
}
