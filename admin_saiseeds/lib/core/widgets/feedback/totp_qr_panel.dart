import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';
import '../../utils/share/phone_number_formatter.dart';
import '../../utils/share/qr_share.dart';
import '../../utils/share/totp_message_builder.dart';
import '../../utils/toast_utils.dart';
import '../buttons/secondary_button.dart';

class TotpQrPanel extends StatefulWidget {
  final String provisioningUri;
  final String phoneNumber;
  final String subjectName;
  final bool isStacked;

  const TotpQrPanel({
    super.key,
    required this.provisioningUri,
    this.phoneNumber = '',
    this.subjectName = '',
    this.isStacked = false,
  });

  @override
  State<TotpQrPanel> createState() => _TotpQrPanelState();
}

class _TotpQrPanelState extends State<TotpQrPanel> {
  static const double _exportPixelRatio = 3.0;

  final GlobalKey _qrKey = GlobalKey();

  String get _uri => widget.provisioningUri.trim();

  bool get _canSendWhatsApp =>
      PhoneNumberFormatter.isDialable(widget.phoneNumber);

  String get _fileName {
    final String slug = widget.subjectName
        .trim()
        .toLowerCase()
        .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
        .replaceAll(RegExp(r'^-+|-+$'), '');
    final String base = slug.isEmpty ? AppStrings.TOTP_QR_FALLBACK_NAME : slug;
    return '$base${AppStrings.TOTP_QR_FILE_SUFFIX}';
  }

  String get _message => TotpMessageBuilder.build(name: widget.subjectName);

  Future<void> _onSendWhatsApp() async {
    final Uint8List? bytes = await _captureQr();
    if (!mounted) return;

    if (bytes != null) {
      final bool shared = await shareQrImage(
        fileName: _fileName,
        bytes: bytes,
        title: AppStrings.TOTP_WHATSAPP_QR_TITLE,
        message: _message,
      );
      if (shared) return;
      if (!mounted) return;

      downloadPngBytes(fileName: _fileName, bytes: bytes);
      ToastUtils.showInfo(context, AppStrings.TOTP_QR_ATTACH_HINT);
    }

    openWhatsApp(phoneNumber: widget.phoneNumber, message: _message);
  }

  Future<void> _onDownloadQr() async {
    final Uint8List? bytes = await _captureQr();
    if (!mounted) return;

    if (bytes == null) {
      ToastUtils.showError(context, AppStrings.TOTP_DOWNLOAD_FAILED);
      return;
    }

    downloadPngBytes(fileName: _fileName, bytes: bytes);
  }

  Future<Uint8List?> _captureQr() async {
    try {
      final RenderRepaintBoundary? boundary =
          _qrKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      if (boundary == null) return null;

      final ui.Image image = await boundary.toImage(
        pixelRatio: _exportPixelRatio,
      );
      final ByteData? data = await image.toByteData(
        format: ui.ImageByteFormat.png,
      );
      return data?.buffer.asUint8List();
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_uri.isEmpty) {
      return Text(
        AppStrings.TOTP_UNAVAILABLE,
        style: AppTypography.bodySmall.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Center(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final double frame = constraints.maxWidth.isFinite
                  ? constraints.maxWidth
                  : AppSizes.qrCodeSize;
              final double side =
                  (frame - (AppSizes.qrFrameInset * 2) - (AppSpacing.xxs * 2))
                      .clamp(0.0, AppSizes.qrCodeSize);

              return RepaintBoundary(
                key: _qrKey,
                child: Container(
                  padding: const EdgeInsets.all(AppSizes.qrFrameInset),
                  decoration: BoxDecoration(
                    color: AppColors.WHITE,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                    border: Border.all(color: AppColors.BORDER),
                  ),
                  child: QrImageView(
                    data: _uri,
                    version: QrVersions.auto,
                    size: side,
                    backgroundColor: AppColors.WHITE,
                    eyeStyle: const QrEyeStyle(
                      eyeShape: QrEyeShape.square,
                      color: AppColors.TEXT_PRIMARY,
                    ),
                    dataModuleStyle: const QrDataModuleStyle(
                      dataModuleShape: QrDataModuleShape.square,
                      color: AppColors.TEXT_PRIMARY,
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        if (widget.isStacked)
          Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              SecondaryButton(
                label: AppStrings.TOTP_SEND_WHATSAPP,
                icon: Icons.chat_outlined,
                onPressed: _canSendWhatsApp ? _onSendWhatsApp : null,
              ),
              const SizedBox(height: AppSpacing.sm),
              SecondaryButton(
                label: AppStrings.TOTP_DOWNLOAD_QR,
                icon: Icons.download_outlined,
                onPressed: _onDownloadQr,
              ),
            ],
          )
        else
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Flexible(
                child: SecondaryButton(
                  label: AppStrings.TOTP_SEND_WHATSAPP,
                  icon: Icons.chat_outlined,
                  onPressed: _canSendWhatsApp ? _onSendWhatsApp : null,
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
              Flexible(
                child: SecondaryButton(
                  label: AppStrings.TOTP_DOWNLOAD_QR,
                  icon: Icons.download_outlined,
                  onPressed: _onDownloadQr,
                ),
              ),
            ],
          ),
        if (!_canSendWhatsApp) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            AppStrings.TOTP_NO_PHONE,
            textAlign: TextAlign.center,
            style: AppTypography.caption.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
        ],
      ],
    );
  }
}
