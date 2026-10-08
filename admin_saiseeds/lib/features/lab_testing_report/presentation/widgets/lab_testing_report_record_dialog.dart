import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/inputs/record_field.dart';
import '../../../../core/widgets/layout/record_field_row.dart';
import '../../data/models/lab_testing_report_model.dart';

/// View-only: a lab test is entered and edited from the lab tester's own
/// app, never from here -- so this dialog never offers an edit mode.
class LabTestingReportRecordDialog extends StatelessWidget {
  final LabTestingReportModel test;

  const LabTestingReportRecordDialog({super.key, required this.test});

  static Future<void> show(BuildContext context, LabTestingReportModel test) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => LabTestingReportRecordDialog(test: test),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.biotech_outlined,
      title: AppStrings.LAB_TESTING_REPORT_DETAIL_TITLE,
      subtitle: AppStrings.LAB_TESTING_REPORT_DETAIL_SUBTITLE,
      mode: RecordDialogMode.view,
      body: _buildFields(),
    );
  }

  Widget _buildFields() {
    final lot = test.inwardRawMaterial;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        RecordFieldRow(
          left: _locked(AppStrings.COLUMN_PRODUCT, test.productName),
          right: _locked(AppStrings.COLUMN_PARTY, test.partyName),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_LOT_NO,
            test.lotNo,
          ),
          right: _locked(AppStrings.COLUMN_QUANTITY, lot?.quantityKg ?? ''),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_LOT_STATUS,
            lot?.status ?? '',
          ),
          right: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_RESULT,
            test.result,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_FIELD_PLANTS,
            '${test.numberOfPlants}',
          ),
          right: _locked(
            AppStrings.LAB_TESTING_REPORT_FIELD_FEMALE_COUNT,
            '${test.femaleCount}',
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_FIELD_OT_COUNT,
            '${test.otCount}',
          ),
          right: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_GENETICAL_IMPURITY,
            _percent(test.geneticalImpurity),
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_GROW_OUT_TEST,
            _percent(test.growOutTest),
          ),
          right: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_TESTED_BY,
            test.testedByName,
          ),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(
            AppStrings.LAB_TESTING_REPORT_COLUMN_TESTED_AT,
            DateFormatter.label(test.testedAt),
          ),
          right: _locked(AppStrings.COLUMN_REFERENCE, test.publicId),
        ),
        const SizedBox(height: AppSpacing.md),
        RecordFieldRow(
          left: _locked(AppStrings.LAB_TESTING_REPORT_FIELD_COMMENT, test.comment),
        ),
      ],
    );
  }

  RecordField _locked(String label, String value) {
    return RecordField(
      controller: TextEditingController(text: value),
      label: label,
      isEditable: false,
      isLocked: true,
    );
  }

  String _percent(String value) {
    final String trimmed = value.trim();
    return trimmed.isEmpty ? '' : '$trimmed%';
  }
}
