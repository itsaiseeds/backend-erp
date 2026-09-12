import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/admins_repository.dart';
import '../../data/models/admin_model.dart';
import '../bloc/admins_cubit.dart';
import '../widgets/admin_detail_dialog.dart';
import '../widgets/admin_form_dialog.dart';
import '../widgets/admins_table.dart';

class AdminsView extends StatelessWidget {
  const AdminsView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<AdminsCubit>(
      create: (context) => AdminsCubit(
        repository: AdminsRepository(apiClient: context.read<ApiClient>()),
      )..loadAdmins(),
      child: const _AdminsContent(),
    );
  }
}

class _AdminsContent extends StatefulWidget {
  const _AdminsContent();

  @override
  State<_AdminsContent> createState() => _AdminsContentState();
}

class _AdminsContentState extends State<_AdminsContent> {
  final GlobalKey<AdminsTableState> _tableKey = GlobalKey<AdminsTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<AdminsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(AdminModel admin) async {
    final AdminsCubit cubit = context.read<AdminsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_ADMIN_TITLE,
      message: AppStrings.DELETE_ADMIN_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteAdmin(admin.id);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.ADMIN_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<AdminsCubit, AdminsState>(
      listenWhen: (previous, current) =>
          current.status == AdminsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.ADMINS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final AdminsCubit cubit = context.read<AdminsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: AdminsTable(
            key: _tableKey,
            admins: state.visibleAdmins,
            isLoading: state.status == AdminsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (admin) => AdminDetailDialog.show(context, admin),
            onEdit: (admin) =>
                AdminFormDialog.show(context, cubit: cubit, admin: admin),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.ADMINS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.ADMINS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadAdmins,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_ADMIN,
                onPressed: () => AdminFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
