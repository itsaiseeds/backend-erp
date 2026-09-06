import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/utils/formatters/role_formatter.dart';
import '../../../../core/widgets/dialogs/app_detail_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/totp_qr_panel.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/admin_model.dart';

class AdminDetailDialog extends StatelessWidget {
  final AdminModel admin;

  const AdminDetailDialog({super.key, required this.admin});

  static Future<void> show(BuildContext context, AdminModel admin) {
    return showDialog<void>(
      context: context,
      builder: (_) => AdminDetailDialog(admin: admin),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.admin_panel_settings_outlined,
      title: AppStrings.ADMIN_DETAIL_TITLE,
      subtitle: AppStrings.DETAIL_SECTION_ACCOUNT_HINT,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          DetailFieldGrid(
            fields: [
              DetailField(label: AppStrings.COLUMN_NAME, value: admin.name),
              DetailField(label: AppStrings.COLUMN_EMAIL, value: admin.email),
              DetailField(
                label: AppStrings.COLUMN_PHONE_NUMBER,
                value: admin.phoneNumber,
              ),
              DetailField(
                label: AppStrings.COLUMN_ROLE,
                value: RoleFormatter.label(admin.role),
              ),
              DetailField(
                label: AppStrings.COLUMN_STOCK_PERMISSION,
                value: admin.canUpdateStockCount
                    ? AppStrings.PERMISSION_ALLOWED
                    : AppStrings.PERMISSION_DENIED,
              ),
              DetailField(
                label: AppStrings.DETAIL_FIELD_CREATED_BY,
                value: admin.createdByName,
              ),
              DetailField(
                label: AppStrings.DETAIL_FIELD_CREATED_AT,
                value: DateFormatter.label(admin.createdAt),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          const AppHairline(),
          const SizedBox(height: AppSpacing.lg),
          Text(
            AppStrings.DETAIL_SECTION_AUTHENTICATOR,
            style: AppTypography.label,
          ),
          const SizedBox(height: AppSpacing.xxs),
          Text(
            AppStrings.DETAIL_SECTION_AUTHENTICATOR_HINT,
            style: AppTypography.bodySmall,
          ),
          const SizedBox(height: AppSpacing.md),
          TotpQrPanel(provisioningUri: admin.provisioningUri),
        ],
      ),
    );
  }
}
