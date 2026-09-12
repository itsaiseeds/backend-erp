import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/dialogs/app_detail_dialog.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../data/models/client_model.dart';
import '../../data/models/client_status.dart';

class ClientDetailDialog extends StatelessWidget {
  final ClientModel client;

  const ClientDetailDialog({super.key, required this.client});

  static Future<void> show(BuildContext context, ClientModel client) {
    return showDialog<void>(
      context: context,
      builder: (_) => ClientDetailDialog(client: client),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppDetailDialog(
      icon: Icons.storefront_outlined,
      title: AppStrings.CLIENT_DETAILS_TITLE,
      subtitle: client.companyName,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: AppBadge(
              label: ClientStatusX.labelOf(client.status),
              variant: client.status == ClientStatus.verified
                  ? AppBadgeVariant.success
                  : AppBadgeVariant.warning,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          DetailFieldGrid(
            fields: [
              DetailField(
                label: AppStrings.COLUMN_COMPANY_NAME,
                value: client.companyName,
              ),
              DetailField(
                label: AppStrings.COLUMN_COMPANY_PHONE,
                value: client.companyPhone,
              ),
              DetailField(
                label: AppStrings.COLUMN_GST_NUMBER,
                value: client.gstNumber,
              ),
              DetailField(
                label: AppStrings.CLIENT_CREATED_BY_LABEL,
                value: client.createdBy,
              ),
            ],
          ),
          if (client.addresses.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            const AppHairline(),
            const SizedBox(height: AppSpacing.md),
            _SectionList(
              title: AppStrings.CLIENT_SECTION_ADDRESSES,
              entries: client.addresses
                  .map(
                    (address) => _Entry(
                      title: address.label.isEmpty
                          ? address.cityName
                          : address.label,
                      subtitle: address.formatted,
                      isPrimary: address.isPrimary,
                    ),
                  )
                  .toList(),
            ),
          ],
          if (client.contacts.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            _SectionList(
              title: AppStrings.CLIENT_SECTION_CONTACTS,
              entries: client.contacts
                  .map(
                    (contact) => _Entry(
                      title: contact.name,
                      subtitle: [
                        contact.phoneNumber,
                        contact.role,
                      ].where((part) => part.trim().isNotEmpty).join(' · '),
                      isPrimary: contact.isPrimary,
                    ),
                  )
                  .toList(),
            ),
          ],
          if (client.transportAgencies.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            _SectionList(
              title: AppStrings.CLIENT_SECTION_TRANSPORT,
              entries: client.transportAgencies
                  .map(
                    (agency) => _Entry(
                      title: agency.name,
                      subtitle: '',
                      isPrimary: agency.isPrimary,
                    ),
                  )
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

class _Entry {
  final String title;
  final String subtitle;
  final bool isPrimary;

  const _Entry({
    required this.title,
    required this.subtitle,
    this.isPrimary = false,
  });
}

class _SectionList extends StatelessWidget {
  final String title;
  final List<_Entry> entries;

  const _SectionList({required this.title, required this.entries});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(title, style: AppTypography.labelStrong),
        const SizedBox(height: AppSpacing.sm),
        for (final entry in entries)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.smd),
              decoration: BoxDecoration(
                color: AppColors.SURFACE,
                border: Border.all(color: AppColors.BORDER),
                borderRadius: BorderRadius.circular(AppRadius.md),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          entry.title.trim().isEmpty
                              ? AppStrings.TABLE_VALUE_UNAVAILABLE
                              : entry.title,
                          style: AppTypography.labelMedium,
                        ),
                        if (entry.subtitle.trim().isNotEmpty) ...[
                          const SizedBox(height: AppSpacing.xxs),
                          Text(entry.subtitle, style: AppTypography.bodySmall),
                        ],
                      ],
                    ),
                  ),
                  if (entry.isPrimary) ...[
                    const SizedBox(width: AppSpacing.sm),
                    const AppBadge(
                      label: AppStrings.CLIENT_PRIMARY_BADGE,
                      variant: AppBadgeVariant.info,
                    ),
                  ],
                ],
              ),
            ),
          ),
      ],
    );
  }
}
