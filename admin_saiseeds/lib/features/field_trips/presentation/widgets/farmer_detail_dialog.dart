import 'package:flutter/material.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/app_badge.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/farmer_model.dart';

class FarmerDetailDialog extends StatelessWidget {
  static const String _COLUMN_TRIP = 'field_trip';
  static const String _COLUMN_VILLAGE = 'village';
  static const String _COLUMN_LAND = 'land_area_bigha';
  static const String _COLUMN_CROPS = 'crops';
  static const String _COLUMN_PRODUCTS = 'products';
  static const String _COLUMN_SALES_PERSON = 'sales_person';
  static const String _COLUMN_VISITED_AT = 'visited_at';

  static const List<AppDataColumn> _VISIT_COLUMNS = [
    AppDataColumn(
      id: _COLUMN_TRIP,
      label: AppStrings.COLUMN_TRIP_ID,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_VILLAGE,
      label: AppStrings.COLUMN_VILLAGE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: _COLUMN_LAND,
      label: AppStrings.COLUMN_LAND_AREA,
      width: AppSizes.tableColumnWidthNarrow,
    ),
    AppDataColumn(
      id: _COLUMN_CROPS,
      label: AppStrings.COLUMN_CROPS,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: _COLUMN_PRODUCTS,
      label: AppStrings.COLUMN_PRODUCTS_USED,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: _COLUMN_SALES_PERSON,
      label: AppStrings.COLUMN_SALES_PERSON,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: _COLUMN_VISITED_AT,
      label: AppStrings.COLUMN_LAST_VISITED,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

  final FarmerModel farmer;

  const FarmerDetailDialog({super.key, required this.farmer});

  static Future<void> show(
    BuildContext context, {
    required FarmerModel farmer,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => FarmerDetailDialog(farmer: farmer),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.agriculture_outlined,
      title: AppStrings.FARMER_DETAIL_TITLE,
      subtitle: AppStrings.FARMER_DETAIL_SUBTITLE,
      mode: RecordDialogMode.view,
      badge: AppBadge(
        label: farmer.usesOurProducts
            ? AppStrings.FARMER_USES_PRODUCTS_YES
            : AppStrings.FARMER_USES_PRODUCTS_NO,
        variant: farmer.usesOurProducts
            ? AppBadgeVariant.success
            : AppBadgeVariant.neutral,
      ),
      extraWidth: AppSizes.recordDialogRoomyBump * 2,
      isTall: true,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          const SectionTitle(
            title: AppStrings.FARMER_SECTION_PROFILE,
            icon: Icons.person_outline_rounded,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _buildProfile(),
          const SizedBox(height: AppSpacing.lg),
          const SectionTitle(
            title: AppStrings.FARMER_SECTION_CROPS,
            icon: Icons.grass_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _ChipList(
            labels: farmer.cropNames,
            emptyMessage: AppStrings.FARMER_CROPS_EMPTY,
          ),
          const SizedBox(height: AppSpacing.lg),
          const SectionTitle(
            title: AppStrings.FARMER_SECTION_PRODUCTS,
            icon: Icons.inventory_2_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _ChipList(
            labels: farmer.productNames,
            emptyMessage: AppStrings.FARMER_PRODUCTS_EMPTY,
            variant: AppBadgeVariant.success,
          ),
          const SizedBox(height: AppSpacing.lg),
          const SectionTitle(
            title: AppStrings.FARMER_SECTION_SALES_PEOPLE,
            icon: Icons.groups_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _buildSalesPeople(),
          const SizedBox(height: AppSpacing.lg),
          SectionTitle(
            title: AppStrings.FARMER_SECTION_VISITS,
            subtitle: '${farmer.visitCount}',
            icon: Icons.map_outlined,
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _buildVisits(),
        ],
      ),
    );
  }

  Widget _buildProfile() {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.COLUMN_FARMER_NAME,
          value: farmer.farmerName,
        ),
        DetailField(
          label: AppStrings.COLUMN_CONTACT_NUMBER,
          value: farmer.contactNumber,
        ),
        DetailField(label: AppStrings.COLUMN_VILLAGE, value: farmer.village),
        DetailField(label: AppStrings.COLUMN_CITY, value: farmer.cityName),
        DetailField(
          label: AppStrings.COLUMN_LAND_AREA,
          value: farmer.landAreaBigha,
        ),
        DetailField(
          label: AppStrings.COLUMN_VISIT_COUNT,
          value: '${farmer.visitCount}',
        ),
        DetailField(
          label: AppStrings.COLUMN_LAST_VISITED,
          value: DateFormatter.instantLabel(farmer.lastVisitedDateTime),
        ),
      ],
    );
  }

  Widget _buildSalesPeople() {
    if (farmer.salesPeople.isEmpty) {
      return _note(AppStrings.FARMER_SALES_PEOPLE_EMPTY);
    }

    return DetailFieldGrid(
      fields: [
        for (final person in farmer.salesPeople)
          DetailField(label: person.name, value: person.phoneNumber),
      ],
    );
  }

  Widget _buildVisits() {
    if (farmer.visits.isEmpty) {
      return _note(AppStrings.FARMER_VISITS_EMPTY);
    }

    return SizedBox(
      height: AppSizes.challanItemsHeight,
      child: AppDataTable<FarmerVisitSummary>(
        items: farmer.visits,
        currentPage: 1,
        totalPages: 0,
        totalItems: farmer.visits.length,
        columns: _VISIT_COLUMNS,
        configKey: 'farmer-visits',
        rowHeight: AppDataTable.standardRowHeight,
        requireColumnSettings: false,
        requireSearchBar: false,
        requirePin: false,
        searchHintText: AppStrings.SEARCH,
        emptyTitle: AppStrings.FARMER_VISITS_EMPTY,
        emptyDescription: AppStrings.TABLE_EMPTY_BODY,
        emptyIcon: Icons.map_outlined,
        cellBuilder: _buildVisitCell,
      ),
    );
  }

  Widget _buildVisitCell(
    BuildContext context,
    FarmerVisitSummary visit,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case _COLUMN_TRIP:
        return _textCell(visit.fieldTripPublicId, isStrong: true);
      case _COLUMN_VILLAGE:
        return _textCell(visit.village);
      case _COLUMN_LAND:
        return _textCell(visit.landAreaBigha);
      case _COLUMN_CROPS:
        return _textCell(visit.crops.map((crop) => crop.name).join(', '));
      case _COLUMN_PRODUCTS:
        return _textCell(
          visit.products.map((product) => product.name).join(', '),
        );
      case _COLUMN_SALES_PERSON:
        return _textCell(visit.salesPersonName);
      case _COLUMN_VISITED_AT:
        return _textCell(DateFormatter.instantLabel(visit.visitedDateTime));
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  Widget _note(String message) {
    return Text(
      message,
      style: AppTypography.bodyMedium.copyWith(color: AppColors.TEXT_SECONDARY),
    );
  }

  Widget _textCell(String value, {bool isStrong = false}) {
    final String text = value.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : value;
    return Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: isStrong
          ? AppTypography.tableCellStrong
          : AppTypography.tableCell.copyWith(color: AppColors.TEXT_PRIMARY),
    );
  }
}

class _ChipList extends StatelessWidget {
  final List<String> labels;
  final String emptyMessage;
  final AppBadgeVariant variant;

  const _ChipList({
    required this.labels,
    required this.emptyMessage,
    this.variant = AppBadgeVariant.neutral,
  });

  @override
  Widget build(BuildContext context) {
    final List<String> present = labels
        .map((label) => label.trim())
        .where((label) => label.isNotEmpty)
        .toList();

    if (present.isEmpty) {
      return Text(
        emptyMessage,
        style: AppTypography.bodyMedium.copyWith(
          color: AppColors.TEXT_SECONDARY,
        ),
      );
    }

    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.sm,
      children: [
        for (final label in present) AppBadge(label: label, variant: variant),
      ],
    );
  }
}
