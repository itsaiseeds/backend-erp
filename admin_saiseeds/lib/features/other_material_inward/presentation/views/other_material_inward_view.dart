import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/parties_service.dart';
import '../../../../core/services/recipes_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../other_raw_materials/data/other_raw_materials_repository.dart';
import '../../../parties/data/parties_repository.dart';
import '../../data/models/other_material_inward_model.dart';
import '../../data/other_material_inward_repository.dart';
import '../bloc/other_material_inward_cubit.dart';
import '../widgets/other_inward_form_dialog.dart';
import '../widgets/other_material_inward_table.dart';

class OtherMaterialInwardView extends StatelessWidget {
  const OtherMaterialInwardView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    RecipesService.instance.repository = OtherRawMaterialsRepository(
      apiClient: apiClient,
    );
    PartiesService.instance.repository = PartiesRepository(
      apiClient: apiClient,
    );

    return BlocProvider<OtherMaterialInwardCubit>(
      create: (context) => OtherMaterialInwardCubit(
        repository: OtherMaterialInwardRepository(apiClient: apiClient),
      )..loadLots(),
      child: const _OtherMaterialInwardContent(),
    );
  }
}

class _OtherMaterialInwardContent extends StatefulWidget {
  const _OtherMaterialInwardContent();

  @override
  State<_OtherMaterialInwardContent> createState() =>
      _OtherMaterialInwardContentState();
}

class _OtherMaterialInwardContentState
    extends State<_OtherMaterialInwardContent> {
  final GlobalKey<OtherMaterialInwardTableState> _tableKey =
      GlobalKey<OtherMaterialInwardTableState>();

  @override
  void initState() {
    super.initState();
    _primeCaches();
  }

  @override
  void dispose() {
    RecipesService.instance.reset();
    PartiesService.instance.reset();
    super.dispose();
  }

  Future<void> _primeCaches() async {
    await Future.wait([
      RecipesService.instance.loadRecipes(forceRefresh: true),
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
    context.read<OtherMaterialInwardCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(OtherMaterialInwardModel lot) async {
    final OtherMaterialInwardCubit cubit = context
        .read<OtherMaterialInwardCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_OTHER_INWARD_TITLE,
      message: AppStrings.DELETE_OTHER_INWARD_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteLot(lot.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.OTHER_INWARD_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<OtherMaterialInwardCubit, OtherMaterialInwardState>(
      listenWhen: (previous, current) =>
          current.status == OtherMaterialInwardStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.OTHER_INWARD_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final OtherMaterialInwardCubit cubit = context
            .read<OtherMaterialInwardCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: OtherMaterialInwardTable(
            key: _tableKey,
            lots: state.lots,
            isLoading: state.status == OtherMaterialInwardStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.OTHER_INWARD_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.OTHER_INWARD_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_OTHER_INWARD,
                onPressed: () =>
                    OtherInwardFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
