import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../data/lab_testing_report_repository.dart';
import '../../data/models/lab_testing_report_model.dart';
import '../bloc/lab_testing_report_cubit.dart';
import '../widgets/lab_testing_report_record_dialog.dart';
import '../widgets/lab_testing_report_table.dart';

class LabTestingReportView extends StatelessWidget {
  const LabTestingReportView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<LabTestingReportCubit>(
      create: (context) => LabTestingReportCubit(
        repository: LabTestingReportRepository(apiClient: apiClient),
      )..loadTests(),
      child: const _LabTestingReportContent(),
    );
  }
}

class _LabTestingReportContent extends StatefulWidget {
  const _LabTestingReportContent();

  @override
  State<_LabTestingReportContent> createState() =>
      _LabTestingReportContentState();
}

class _LabTestingReportContentState extends State<_LabTestingReportContent> {
  final GlobalKey<LabTestingReportTableState> _tableKey =
      GlobalKey<LabTestingReportTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<LabTestingReportCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<LabTestingReportCubit, LabTestingReportState>(
      listenWhen: (previous, current) =>
          current.status == LabTestingReportStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.LAB_TESTING_REPORT_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final LabTestingReportCubit cubit = context
            .read<LabTestingReportCubit>();
        final List<LabTestingReportModel> visibleTests = state.visibleTests;

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: LabTestingReportTable(
            key: _tableKey,
            tests: visibleTests,
            isLoading: state.status == LabTestingReportStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.hasSearch ? visibleTests.length : state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: (test) => LabTestingReportRecordDialog.show(context, test),
            emptyTitle: state.isEmptySource
                ? AppStrings.LAB_TESTING_REPORT_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.LAB_TESTING_REPORT_EMPTY_STATE_BODY
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
