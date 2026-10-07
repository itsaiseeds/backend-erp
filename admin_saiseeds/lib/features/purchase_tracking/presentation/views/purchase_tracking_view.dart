import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/models/purchase_tracking_model.dart';
import '../../data/purchase_tracking_repository.dart';
import '../bloc/purchase_tracking_cubit.dart';
import '../widgets/purchase_tracking_form_dialog.dart';
import '../widgets/purchase_tracking_record_dialog.dart';
import '../widgets/purchase_tracking_table.dart';

class PurchaseTrackingView extends StatelessWidget {
  const PurchaseTrackingView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<PurchaseTrackingCubit>(
      create: (context) => PurchaseTrackingCubit(
        repository: PurchaseTrackingRepository(apiClient: apiClient),
      )..loadEntries(),
      child: const _PurchaseTrackingContent(),
    );
  }
}

class _PurchaseTrackingContent extends StatefulWidget {
  const _PurchaseTrackingContent();

  @override
  State<_PurchaseTrackingContent> createState() =>
      _PurchaseTrackingContentState();
}

class _PurchaseTrackingContentState extends State<_PurchaseTrackingContent> {
  final GlobalKey<PurchaseTrackingTableState> _tableKey =
      GlobalKey<PurchaseTrackingTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<PurchaseTrackingCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(PurchaseTrackingModel entry) async {
    final PurchaseTrackingCubit cubit = context.read<PurchaseTrackingCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_PURCHASE_TRACKING_TITLE,
      message: AppStrings.DELETE_PURCHASE_TRACKING_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteEntry(entry.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(
        context,
        AppStrings.PURCHASE_TRACKING_DELETED_TITLE,
      );
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<PurchaseTrackingCubit, PurchaseTrackingState>(
      listenWhen: (previous, current) =>
          current.status == PurchaseTrackingStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.PURCHASE_TRACKING_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final PurchaseTrackingCubit cubit = context
            .read<PurchaseTrackingCubit>();
        final List<PurchaseTrackingModel> visibleEntries =
            state.visibleEntries;

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: PurchaseTrackingTable(
            key: _tableKey,
            entries: visibleEntries,
            isLoading: state.status == PurchaseTrackingStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.hasSearch
                ? visibleEntries.length
                : state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: (entry) => PurchaseTrackingRecordDialog.show(
              context,
              entry,
              cubit: cubit,
            ),
            onEdit: (entry) => PurchaseTrackingRecordDialog.show(
              context,
              entry,
              cubit: cubit,
              initialMode: RecordDialogMode.edit,
            ),
            onDelete: _onDelete,
            isMutating: state.isMutating,
            emptyTitle: state.isEmptySource
                ? AppStrings.PURCHASE_TRACKING_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.PURCHASE_TRACKING_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_PURCHASE_TRACKING_ENTRY,
                onPressed: () =>
                    PurchaseTrackingFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
