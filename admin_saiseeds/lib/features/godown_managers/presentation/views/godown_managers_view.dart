import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/godown_managers_repository.dart';
import '../../data/models/godown_manager_model.dart';
import '../bloc/godown_managers_cubit.dart';
import '../widgets/godown_manager_form_dialog.dart';
import '../widgets/godown_manager_record_dialog.dart';
import '../widgets/godown_managers_table.dart';

class GodownManagersView extends StatelessWidget {
  const GodownManagersView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<GodownManagersCubit>(
      create: (context) => GodownManagersCubit(
        repository: GodownManagersRepository(
          apiClient: context.read<ApiClient>(),
        ),
      )..loadGodownManagers(),
      child: const _GodownManagersContent(),
    );
  }
}

class _GodownManagersContent extends StatefulWidget {
  const _GodownManagersContent();

  @override
  State<_GodownManagersContent> createState() =>
      _GodownManagersContentState();
}

class _GodownManagersContentState extends State<_GodownManagersContent> {
  final GlobalKey<GodownManagersTableState> _tableKey =
      GlobalKey<GodownManagersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<GodownManagersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(GodownManagerModel godownManager) async {
    final GodownManagersCubit cubit = context.read<GodownManagersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_GODOWN_MANAGER_TITLE,
      message: AppStrings.DELETE_GODOWN_MANAGER_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteGodownManager(godownManager.id);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.GODOWN_MANAGER_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<GodownManagersCubit, GodownManagersState>(
      listenWhen: (previous, current) =>
          current.status == GodownManagersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.GODOWN_MANAGERS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final GodownManagersCubit cubit = context.read<GodownManagersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: GodownManagersTable(
            key: _tableKey,
            godownManagers: state.visibleGodownManagers,
            isLoading: state.status == GodownManagersStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (manager) => GodownManagerRecordDialog.show(
              context,
              manager,
              cubit: cubit,
            ),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.GODOWN_MANAGERS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.GODOWN_MANAGERS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadGodownManagers,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_GODOWN_MANAGER,
                onPressed: () =>
                    GodownManagerFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
