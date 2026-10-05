import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/date_formatter.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/detail_field.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/loaders/shimmer_rows.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../data/models/farmer_visit_model.dart';
import '../../data/models/field_trip_model.dart';
import '../bloc/field_trips_cubit.dart';
import 'field_trip_status_badge.dart';

class FieldTripDetailDialog extends StatefulWidget {
  final FieldTripModel trip;

  const FieldTripDetailDialog({super.key, required this.trip});

  static Future<void> show(
    BuildContext context, {
    required FieldTripsCubit cubit,
    required FieldTripModel trip,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<FieldTripsCubit>.value(
        value: cubit,
        child: FieldTripDetailDialog(trip: trip),
      ),
    );
  }

  @override
  State<FieldTripDetailDialog> createState() => _FieldTripDetailDialogState();
}

class _FieldTripDetailDialogState extends State<FieldTripDetailDialog> {
  static const List<IconData> _ICONS = [
    Icons.place_outlined,
    Icons.timeline_outlined,
    Icons.agriculture_outlined,
  ];

  static const List<String> _STEPS = [
    AppStrings.FIELD_TRIP_SECTION_PLAN,
    AppStrings.FIELD_TRIP_SECTION_PROGRESS,
    AppStrings.FIELD_TRIP_SECTION_FARMERS,
  ];

  static const List<String> _CAPTIONS = [
    AppStrings.FIELD_TRIP_STEP_PLAN_CAPTION,
    AppStrings.FIELD_TRIP_STEP_PROGRESS_CAPTION,
    AppStrings.FIELD_TRIP_STEP_FARMERS_CAPTION,
  ];

  static const String _COLUMN_FARMER = 'farmer_name';
  static const String _COLUMN_CONTACT = 'contact_number';
  static const String _COLUMN_VILLAGE = 'village';
  static const String _COLUMN_LAND = 'land_area_bigha';
  static const String _COLUMN_CROPS = 'crops';
  static const String _COLUMN_USES_PRODUCTS = 'uses_our_products';
  static const String _COLUMN_PRODUCTS = 'products';

  static const List<AppDataColumn> _FARMER_COLUMNS = [
    AppDataColumn(
      id: _COLUMN_FARMER,
      label: AppStrings.COLUMN_FARMER_NAME,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: _COLUMN_CONTACT,
      label: AppStrings.COLUMN_CONTACT_NUMBER,
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
      id: _COLUMN_USES_PRODUCTS,
      label: AppStrings.COLUMN_USES_OUR_PRODUCTS,
      width: AppSizes.tableColumnWidthNarrow,
      isCenter: true,
    ),
    AppDataColumn(
      id: _COLUMN_PRODUCTS,
      label: AppStrings.COLUMN_PRODUCTS_USED,
      width: AppSizes.tableColumnWidthWide,
    ),
  ];

  List<FarmerVisitModel> _visits = const [];
  bool _isLoadingVisits = true;
  bool _hasVisitsError = false;
  int _stepIndex = 0;

  FieldTripModel get _trip => widget.trip;

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  @override
  void initState() {
    super.initState();
    _loadVisits();
  }

  Future<void> _loadVisits() async {
    try {
      final List<FarmerVisitModel> visits = await context
          .read<FieldTripsCubit>()
          .loadFarmerVisits(_trip.publicId);
      if (!mounted) return;
      setState(() {
        _visits = visits;
        _isLoadingVisits = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _hasVisitsError = true;
        _isLoadingVisits = false;
      });
    }
  }

  void _goTo(int index) =>
      setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.map_outlined,
      title: AppStrings.FIELD_TRIP_DETAIL_TITLE,
      subtitle: _subtitle,
      mode: RecordDialogMode.view,
      showFooterInViewMode: true,
      badge: FieldTripStatusBadge(trip: _trip),
      extraWidth: AppSizes.recordDialogRoomyBump * 2,
      isTall: true,
      onCancelEdit: _isFirstStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CLOSE : AppStrings.STEP_BACK,
      onSubmit: _isLastStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex + 1),
      submitLabel: _isLastStep ? AppStrings.CLOSE : AppStrings.STEP_NEXT,
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          SectionTitle(
            title: _STEPS[_stepIndex],
            subtitle: _isLastStep ? '${_trip.farmerVisitCount}' : null,
            icon: _ICONS[_stepIndex],
            hasRule: true,
          ),
          const SizedBox(height: AppSpacing.md),
          _buildStep(),
        ],
      ),
    );
  }

  String get _subtitle =>
      '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
      '${AppStrings.LABEL_SEPARATOR} ${_CAPTIONS[_stepIndex]}';

  Widget _buildStep() {
    switch (_stepIndex) {
      case 1:
        return _buildProgress();
      case 2:
        return _buildFarmers();
      default:
        return _buildPlan();
    }
  }

  Widget _buildPlan() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildPlanFields(),
        const SizedBox(height: AppSpacing.lg),
        const SectionTitle(
          title: AppStrings.FIELD_TRIP_SECTION_PEOPLE,
          icon: Icons.groups_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.md),
        _buildPeople(),
      ],
    );
  }

  Widget _buildProgress() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildTimeline(),
        const SizedBox(height: AppSpacing.lg),
        const SectionTitle(
          title: AppStrings.FIELD_TRIP_SECTION_APPROVAL,
          icon: Icons.verified_outlined,
          hasRule: true,
        ),
        const SizedBox(height: AppSpacing.md),
        _buildApproval(),
      ],
    );
  }

  Widget _buildPlanFields() {
    return DetailFieldGrid(
      fields: [
        DetailField(label: AppStrings.COLUMN_TRIP_ID, value: _trip.publicId),
        DetailField(label: AppStrings.COLUMN_CITY, value: _trip.cityName),
        DetailField(label: AppStrings.COLUMN_VILLAGE, value: _trip.village),
        DetailField(label: AppStrings.COLUMN_STATUS, value: _trip.statusLabel),
        DetailField(
          label: AppStrings.COLUMN_EXPECTED_START,
          value: DateFormatter.instantLabel(_trip.expectedStartDateTime),
        ),
        DetailField(
          label: AppStrings.COLUMN_EXPECTED_END,
          value: DateFormatter.instantLabel(_trip.expectedEndDateTime),
        ),
      ],
    );
  }

  Widget _buildPeople() {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.COLUMN_SALES_PERSON,
          value: _trip.salesPersonName,
        ),
        DetailField(
          label: AppStrings.COLUMN_PHONE_NUMBER,
          value: _trip.salesPersonPhone,
        ),
      ],
    );
  }

  Widget _buildApproval() {
    return DetailFieldGrid(
      fields: [
        DetailField(
          label: AppStrings.COLUMN_APPROVED_BY,
          value: _trip.approverName,
        ),
        DetailField(
          label: AppStrings.COLUMN_APPROVED_AT,
          value: DateFormatter.instantLabel(_trip.approvedDateTime),
        ),
      ],
    );
  }

  Widget _buildTimeline() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        _TimelineStep(
          label: AppStrings.FIELD_TRIP_TIMELINE_PLANNED,
          at: _trip.createdDateTime,
          isFirst: true,
        ),
        _TimelineStep(
          label: AppStrings.FIELD_TRIP_TIMELINE_APPROVED,
          at: _trip.approvedDateTime,
        ),
        _TimelineStep(
          label: AppStrings.FIELD_TRIP_TIMELINE_STARTED,
          at: _trip.startedDateTime,
        ),
        _TimelineStep(
          label: AppStrings.FIELD_TRIP_TIMELINE_ENDED,
          at: _trip.endedDateTime,
          isLast: true,
        ),
      ],
    );
  }

  Widget _buildFarmers() {
    if (_isLoadingVisits) {
      return const ShimmerRows(rowCount: 3);
    }

    if (_hasVisitsError) {
      return _buildNote(AppStrings.FIELD_TRIP_FARMERS_FAILED);
    }

    if (_visits.isEmpty) {
      return _buildNote(AppStrings.FIELD_TRIP_FARMERS_EMPTY);
    }

    return SizedBox(
      height: AppSizes.challanItemsHeight,
      child: AppDataTable<FarmerVisitModel>(
        items: _visits,
        currentPage: 1,
        totalPages: 0,
        totalItems: _visits.length,
        columns: _FARMER_COLUMNS,
        configKey: 'field-trip-farmer-visits',
        rowHeight: AppDataTable.standardRowHeight,
        requireColumnSettings: false,
        requireSearchBar: false,
        requirePin: false,
        searchHintText: AppStrings.SEARCH,
        emptyTitle: AppStrings.FIELD_TRIP_FARMERS_EMPTY,
        emptyDescription: AppStrings.TABLE_EMPTY_BODY,
        emptyIcon: Icons.agriculture_outlined,
        cellBuilder: _buildFarmerCell,
      ),
    );
  }

  Widget _buildNote(String message) {
    return Text(
      message,
      style: AppTypography.bodyMedium.copyWith(color: AppColors.TEXT_SECONDARY),
    );
  }

  Widget _buildFarmerCell(
    BuildContext context,
    FarmerVisitModel visit,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case _COLUMN_FARMER:
        return _textCell(visit.farmerName, isStrong: true);
      case _COLUMN_CONTACT:
        return _textCell(visit.contactNumber);
      case _COLUMN_VILLAGE:
        return _textCell(visit.village);
      case _COLUMN_LAND:
        return _textCell(visit.landAreaBigha);
      case _COLUMN_CROPS:
        return _textCell(visit.cropNames);
      case _COLUMN_USES_PRODUCTS:
        return Align(
          alignment: Alignment.center,
          child: Icon(
            visit.usesOurProducts
                ? Icons.check_circle_outline_rounded
                : Icons.remove_circle_outline_rounded,
            size: AppSizes.iconMd,
            color: visit.usesOurProducts
                ? AppColors.SUCCESS
                : AppColors.TEXT_DISABLED,
          ),
        );
      case _COLUMN_PRODUCTS:
        return _textCell(visit.productNames);
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
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

/// One rung of the lifecycle. A stage the trip has not reached yet keeps its
/// place in the ladder but reads as pending, so the whole path stays visible.
class _TimelineStep extends StatelessWidget {
  final String label;
  final DateTime? at;
  final bool isFirst;
  final bool isLast;

  const _TimelineStep({
    required this.label,
    required this.at,
    this.isFirst = false,
    this.isLast = false,
  });

  bool get _isReached => at != null;

  @override
  Widget build(BuildContext context) {
    final Color accent = _isReached
        ? AppColors.PRIMARY
        : AppColors.BORDER_STRONG;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: AppSizes.iconLg,
            child: Column(
              children: [
                Expanded(child: _rail(isVisible: !isFirst)),
                Container(
                  width: AppSizes.profileMarkerDot,
                  height: AppSizes.profileMarkerDot,
                  decoration: BoxDecoration(
                    color: accent,
                    shape: BoxShape.circle,
                  ),
                ),
                Expanded(child: _rail(isVisible: !isLast)),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      label,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.labelStrong.copyWith(
                        color: _isReached
                            ? AppColors.TEXT_PRIMARY
                            : AppColors.TEXT_DISABLED,
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpacing.sm),
                  Text(
                    _isReached
                        ? DateFormatter.instantLabel(at)
                        : AppStrings.FIELD_TRIP_TIMELINE_PENDING,
                    style: AppTypography.bodySmall.copyWith(
                      color: _isReached
                          ? AppColors.TEXT_SECONDARY
                          : AppColors.TEXT_DISABLED,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _rail({required bool isVisible}) {
    return Container(
      width: AppSizes.sidebarGroupSpineWidth,
      color: isVisible ? AppColors.DIVIDER : AppColors.TRANSPARENT,
    );
  }
}
