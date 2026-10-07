import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/lab_testers_repository.dart';
import '../../data/models/lab_tester_model.dart';
import '../bloc/lab_testers_cubit.dart';
import '../widgets/lab_tester_form_dialog.dart';
import '../widgets/lab_tester_record_dialog.dart';
import '../widgets/lab_testers_table.dart';

class LabTestersView extends StatelessWidget {
  const LabTestersView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<LabTestersCubit>(
      create: (context) => LabTestersCubit(
        repository: LabTestersRepository(apiClient: context.read<ApiClient>()),
      )..loadLabTesters(),
      child: const _LabTestersContent(),
    );
  }
}

class _LabTestersContent extends StatefulWidget {
  const _LabTestersContent();

  @override
  State<_LabTestersContent> createState() => _LabTestersContentState();
}

class _LabTestersContentState extends State<_LabTestersContent> {
  final GlobalKey<LabTestersTableState> _tableKey =
      GlobalKey<LabTestersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<LabTestersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(LabTesterModel labTester) async {
    final LabTestersCubit cubit = context.read<LabTestersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_LAB_TESTER_TITLE,
      message: AppStrings.DELETE_LAB_TESTER_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteLabTester(labTester.id);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.LAB_TESTER_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<LabTestersCubit, LabTestersState>(
      listenWhen: (previous, current) =>
          current.status == LabTestersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.LAB_TESTERS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final LabTestersCubit cubit = context.read<LabTestersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: LabTestersTable(
            key: _tableKey,
            labTesters: state.visibleLabTesters,
            isLoading: state.status == LabTestersStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (tester) =>
                LabTesterRecordDialog.show(context, tester, cubit: cubit),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.LAB_TESTERS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.LAB_TESTERS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadLabTesters,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_LAB_TESTER,
                onPressed: () =>
                    LabTesterFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
