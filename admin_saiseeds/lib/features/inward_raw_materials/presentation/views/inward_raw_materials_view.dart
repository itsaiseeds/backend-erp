import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/parties_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../parties/data/parties_repository.dart';
import '../../../products/data/products_repository.dart';
import '../../data/inward_raw_materials_repository.dart';
import '../../data/models/inward_raw_material_model.dart';
import '../bloc/inward_raw_materials_cubit.dart';
import '../widgets/inward_form_dialog.dart';
import '../widgets/inward_raw_materials_table.dart';
import '../widgets/inward_record_dialog.dart';

class InwardRawMaterialsView extends StatelessWidget {
  const InwardRawMaterialsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );
    PartiesService.instance.repository = PartiesRepository(
      apiClient: apiClient,
    );

    return BlocProvider<InwardRawMaterialsCubit>(
      create: (context) => InwardRawMaterialsCubit(
        repository: InwardRawMaterialsRepository(apiClient: apiClient),
      )..loadLots(),
      child: const _InwardRawMaterialsContent(),
    );
  }
}

class _InwardRawMaterialsContent extends StatefulWidget {
  const _InwardRawMaterialsContent();

  @override
  State<_InwardRawMaterialsContent> createState() =>
      _InwardRawMaterialsContentState();
}

class _InwardRawMaterialsContentState
    extends State<_InwardRawMaterialsContent> {
  final GlobalKey<InwardRawMaterialsTableState> _tableKey =
      GlobalKey<InwardRawMaterialsTableState>();

  @override
  void initState() {
    super.initState();
    _primeCaches();
  }

  @override
  void dispose() {
    ProductsService.instance.reset();
    PartiesService.instance.reset();
    super.dispose();
  }

  Future<void> _primeCaches() async {
    await Future.wait([
      ProductsService.instance.loadProducts(forceRefresh: true),
      PartiesService.instance.loadParties(forceRefresh: true),
    ]);
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
    context.read<InwardRawMaterialsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(InwardRawMaterialModel lot) async {
    final InwardRawMaterialsCubit cubit = context
        .read<InwardRawMaterialsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_INWARD_TITLE,
      message: AppStrings.DELETE_INWARD_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteLot(lot.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.INWARD_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<InwardRawMaterialsCubit, InwardRawMaterialsState>(
      listenWhen: (previous, current) =>
          current.status == InwardRawMaterialsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.INWARD_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final InwardRawMaterialsCubit cubit = context
            .read<InwardRawMaterialsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: InwardRawMaterialsTable(
            key: _tableKey,
            lots: state.lots,
            isLoading: state.status == InwardRawMaterialsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            onView: (lot) =>
                InwardRecordDialog.show(context, lot, cubit: cubit),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.INWARD_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.INWARD_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_INWARD,
                onPressed: () => InwardFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
