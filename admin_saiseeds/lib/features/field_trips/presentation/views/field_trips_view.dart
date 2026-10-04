import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/metadata_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/field_trips_repository.dart';
import '../../data/models/field_trip_model.dart';
import '../bloc/field_trips_cubit.dart';
import '../widgets/field_trip_detail_dialog.dart';
import '../widgets/field_trip_form_dialog.dart';
import '../widgets/field_trips_table.dart';

class FieldTripsView extends StatelessWidget {
  const FieldTripsView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<FieldTripsCubit>(
      create: (context) => FieldTripsCubit(
        repository: FieldTripsRepository(apiClient: context.read<ApiClient>()),
      )..loadTrips(),
      child: const _FieldTripsContent(),
    );
  }
}

class _FieldTripsContent extends StatefulWidget {
  const _FieldTripsContent();

  @override
  State<_FieldTripsContent> createState() => _FieldTripsContentState();
}

class _FieldTripsContentState extends State<_FieldTripsContent> {
  final GlobalKey<FieldTripsTableState> _tableKey =
      GlobalKey<FieldTripsTableState>();

  @override
  void initState() {
    super.initState();
    _primeCities();
  }

  /// The edit dialog picks a city from the cached list, so it must be warm
  /// before a row is opened.
  Future<void> _primeCities() async {
    await MetadataService.instance.loadCities();
    if (mounted) setState(() {});
  }

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<FieldTripsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onApprove(FieldTripModel trip) async {
    if (!trip.canApprove) return;

    await _confirmAndRun(
      title: AppStrings.FIELD_TRIP_APPROVE_TITLE,
      message: '${trip.publicId} — ${AppStrings.FIELD_TRIP_APPROVE_BODY}',
      confirmLabel: AppStrings.FIELD_TRIP_APPROVE,
      successMessage: AppStrings.FIELD_TRIP_APPROVED_DONE,
      action: (cubit) => cubit.approveTrip(trip.publicId),
    );
  }

  Future<void> _onUnapprove(FieldTripModel trip) async {
    if (!trip.canUnapprove) return;

    await _confirmAndRun(
      title: AppStrings.FIELD_TRIP_UNAPPROVE_TITLE,
      message: '${trip.publicId} — ${AppStrings.FIELD_TRIP_UNAPPROVE_BODY}',
      confirmLabel: AppStrings.FIELD_TRIP_UNAPPROVE,
      successMessage: AppStrings.FIELD_TRIP_UNAPPROVED_DONE,
      action: (cubit) => cubit.unapproveTrip(trip.publicId),
    );
  }

  Future<void> _onDelete(FieldTripModel trip) async {
    if (!trip.canDelete) return;

    await _confirmAndRun(
      title: AppStrings.DELETE_FIELD_TRIP_TITLE,
      message: AppStrings.DELETE_FIELD_TRIP_BODY,
      confirmLabel: AppStrings.DELETE,
      successMessage: AppStrings.FIELD_TRIP_DELETED_TITLE,
      isDangerous: true,
      action: (cubit) => cubit.deleteTrip(trip.publicId),
    );
  }

  Future<void> _confirmAndRun({
    required String title,
    required String message,
    required String confirmLabel,
    required String successMessage,
    required Future<bool> Function(FieldTripsCubit cubit) action,
    bool isDangerous = false,
  }) async {
    final FieldTripsCubit cubit = context.read<FieldTripsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: title,
      message: message,
      confirmLabel: confirmLabel,
      isDangerous: isDangerous,
    );
    if (!confirmed) return;

    final bool succeeded = await action(cubit);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, successMessage);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<FieldTripsCubit, FieldTripsState>(
      listenWhen: (previous, current) =>
          current.status == FieldTripsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.FIELD_TRIPS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final FieldTripsCubit cubit = context.read<FieldTripsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: FieldTripsTable(
            key: _tableKey,
            trips: state.trips,
            isLoading: state.status == FieldTripsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: (trip) =>
                FieldTripDetailDialog.show(context, cubit: cubit, trip: trip),
            onEdit: (trip) =>
                FieldTripFormDialog.show(context, cubit: cubit, trip: trip),
            onApprove: _onApprove,
            onUnapprove: _onUnapprove,
            onDelete: _onDelete,
            isMutating: state.isMutating,
            emptyTitle: state.isEmptySource
                ? AppStrings.FIELD_TRIPS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.FIELD_TRIPS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
            ],
          ),
        );
      },
    );
  }
}
