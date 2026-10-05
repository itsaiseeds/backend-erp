import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../products/data/products_repository.dart';
import '../../data/models/waste_model.dart';
import '../../data/waste_management_repository.dart';
import '../bloc/waste_management_cubit.dart';
import '../widgets/waste_form_dialog.dart';
import '../widgets/waste_management_table.dart';
import '../widgets/waste_record_dialog.dart';

class WasteManagementView extends StatelessWidget {
  const WasteManagementView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );

    return BlocProvider<WasteManagementCubit>(
      create: (context) => WasteManagementCubit(
        repository: WasteManagementRepository(apiClient: apiClient),
      )..loadWastes(),
      child: const _WasteManagementContent(),
    );
  }
}

class _WasteManagementContent extends StatefulWidget {
  const _WasteManagementContent();

  @override
  State<_WasteManagementContent> createState() =>
      _WasteManagementContentState();
}

class _WasteManagementContentState extends State<_WasteManagementContent> {
  final GlobalKey<WasteManagementTableState> _tableKey =
      GlobalKey<WasteManagementTableState>();

  @override
  void initState() {
    super.initState();
    _primeProducts();
  }

  @override
  void dispose() {
    ProductsService.instance.reset();
    super.dispose();
  }

  Future<void> _primeProducts() async {
    await ProductsService.instance.loadProducts(forceRefresh: true);
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
    context.read<WasteManagementCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(WasteModel waste) async {
    final WasteManagementCubit cubit = context.read<WasteManagementCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_WASTE_TITLE,
      message: AppStrings.DELETE_WASTE_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteWaste(waste.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.WASTE_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<WasteManagementCubit, WasteManagementState>(
      listenWhen: (previous, current) =>
          current.status == WasteManagementStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.WASTE_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final WasteManagementCubit cubit = context.read<WasteManagementCubit>();
        final List<WasteModel> visibleWastes = state.visibleWastes;

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: WasteManagementTable(
            key: _tableKey,
            wastes: visibleWastes,
            isLoading: state.status == WasteManagementStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.hasSearch
                ? visibleWastes.length
                : state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: (waste) =>
                WasteRecordDialog.show(context, waste, cubit: cubit),
            onEdit: (waste) => WasteRecordDialog.show(
              context,
              waste,
              cubit: cubit,
              initialMode: RecordDialogMode.edit,
            ),
            onDelete: _onDelete,
            isMutating: state.isMutating,
            emptyTitle: state.isEmptySource
                ? AppStrings.WASTE_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.WASTE_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_WASTE,
                onPressed: () => WasteFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
