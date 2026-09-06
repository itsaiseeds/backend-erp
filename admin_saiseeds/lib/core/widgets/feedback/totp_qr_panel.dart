import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';
import '../../constants/app_strings.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_spacing.dart';
import '../../theme/app_typography.dart';

class TotpQrPanel extends StatelessWidget {
  final String provisioningUri;

  const TotpQrPanel({super.key, required this.provisioningUri});

  @override
  Widget build(BuildContext context) {
    final String uri = provisioningUri.trim();

    if (uri.isEmpty) {
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
          child: Container(
            padding: const EdgeInsets.all(AppSizes.qrFrameInset),
            decoration: BoxDecoration(
              color: AppColors.WHITE,
              borderRadius: BorderRadius.circular(AppRadius.md),
              border: Border.all(color: AppColors.BORDER),
            ),
            child: QrImageView(
              data: uri,
              version: QrVersions.auto,
              size: AppSizes.qrCodeSize,
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
        ),
      ],
    );
  }
}
