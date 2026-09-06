import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/models/sales_person_model.dart';
import '../../data/sales_people_repository.dart';
import '../bloc/sales_people_cubit.dart';
import '../widgets/sales_people_table.dart';
import '../widgets/sales_person_detail_dialog.dart';
import '../widgets/sales_person_form_dialog.dart';

class SalesPeopleView extends StatelessWidget {
  const SalesPeopleView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<SalesPeopleCubit>(
      create: (context) => SalesPeopleCubit(
        repository: SalesPeopleRepository(
          apiClient: context.read<ApiClient>(),
        ),
      )..loadSalesPeople(),
      child: const _SalesPeopleContent(),
    );
  }
}

class _SalesPeopleContent extends StatefulWidget {
  const _SalesPeopleContent();

  @override
  State<_SalesPeopleContent> createState() => _SalesPeopleContentState();
}

class _SalesPeopleContentState extends State<_SalesPeopleContent> {
  final GlobalKey<SalesPeopleTableState> _tableKey =
      GlobalKey<SalesPeopleTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<SalesPeopleCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(SalesPersonModel salesPerson) async {
    final SalesPeopleCubit cubit = context.read<SalesPeopleCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_SALES_PERSON_TITLE,
      message: AppStrings.DELETE_SALES_PERSON_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteSalesPerson(salesPerson.id);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.SALES_PERSON_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<SalesPeopleCubit, SalesPeopleState>(
      listenWhen: (previous, current) =>
          current.status == SalesPeopleStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.SALES_PEOPLE_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final SalesPeopleCubit cubit = context.read<SalesPeopleCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: SalesPeopleTable(
            key: _tableKey,
            salesPeople: state.visibleSalesPeople,
            isLoading: state.status == SalesPeopleStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (person) => SalesPersonDetailDialog.show(context, person),
            onEdit: (person) => SalesPersonFormDialog.show(
              context,
              cubit: cubit,
              salesPerson: person,
            ),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.SALES_PEOPLE_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.SALES_PEOPLE_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadSalesPeople,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_SALES_PERSON,
                onPressed: () =>
                    SalesPersonFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
