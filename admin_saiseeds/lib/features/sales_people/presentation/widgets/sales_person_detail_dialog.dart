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
import '../../data/models/sales_person_model.dart';

class SalesPersonDetailDialog extends StatelessWidget {
  final SalesPersonModel salesPerson;

  const SalesPersonDetailDialog({super.key, required this.salesPerson});

  static Future<void> show(BuildContext context, SalesPersonModel person) {
    return showDialog<void>(
      context: context,
      builder: (_) => SalesPersonDetailDialog(salesPerson: person),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.groups_outlined,
      title: AppStrings.SALES_PERSON_DETAIL_TITLE,
      subtitle: AppStrings.DETAIL_SECTION_ACCOUNT_HINT,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          DetailFieldGrid(
            fields: [
              DetailField(
                label: AppStrings.COLUMN_NAME,
                value: salesPerson.name,
              ),
              DetailField(
                label: AppStrings.COLUMN_EMAIL,
                value: salesPerson.email,
              ),
              DetailField(
                label: AppStrings.COLUMN_PHONE_NUMBER,
                value: salesPerson.phoneNumber,
              ),
              DetailField(
                label: AppStrings.COLUMN_ROLE,
                value: RoleFormatter.label(salesPerson.role),
              ),
              DetailField(
                label: AppStrings.COLUMN_CITY,
                value: salesPerson.cityName,
              ),
              DetailField(
                label: AppStrings.DETAIL_FIELD_CREATED_BY,
                value: salesPerson.createdByName,
              ),
              DetailField(
                label: AppStrings.DETAIL_FIELD_CREATED_AT,
                value: DateFormatter.label(salesPerson.createdAt),
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
          TotpQrPanel(provisioningUri: salesPerson.provisioningUri),
        ],
      ),
    );
  }
}
