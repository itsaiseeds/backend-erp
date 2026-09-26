import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/material_types_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../products/data/products_repository.dart';
import '../../data/models/other_material_recipe_model.dart';
import '../../data/other_raw_materials_repository.dart';
import '../bloc/other_raw_materials_cubit.dart';
import '../widgets/other_raw_materials_table.dart';
import '../widgets/recipe_form_dialog.dart';
import '../widgets/recipe_record_dialog.dart';

class OtherRawMaterialsView extends StatelessWidget {
  const OtherRawMaterialsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    final OtherRawMaterialsRepository repository = OtherRawMaterialsRepository(
      apiClient: apiClient,
    );

    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );
    MaterialTypesService.instance.repository = repository;

    return BlocProvider<OtherRawMaterialsCubit>(
      create: (context) =>
          OtherRawMaterialsCubit(repository: repository)..loadRecipes(),
      child: const _OtherRawMaterialsContent(),
    );
  }
}

class _OtherRawMaterialsContent extends StatefulWidget {
  const _OtherRawMaterialsContent();

  @override
  State<_OtherRawMaterialsContent> createState() =>
      _OtherRawMaterialsContentState();
}

class _OtherRawMaterialsContentState extends State<_OtherRawMaterialsContent> {
  final GlobalKey<OtherRawMaterialsTableState> _tableKey =
      GlobalKey<OtherRawMaterialsTableState>();

  @override
  void initState() {
    super.initState();
    _primeCaches();
  }

  @override
  void dispose() {
    ProductsService.instance.reset();
    MaterialTypesService.instance.reset();
    super.dispose();
  }

  Future<void> _primeCaches() async {
    await Future.wait([
      ProductsService.instance.loadProducts(forceRefresh: true),
      MaterialTypesService.instance.loadMaterialTypes(forceRefresh: true),
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
    context.read<OtherRawMaterialsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(OtherMaterialRecipeModel recipe) async {
    final OtherRawMaterialsCubit cubit = context.read<OtherRawMaterialsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_RECIPE_TITLE,
      message: AppStrings.DELETE_RECIPE_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteRecipe(recipe.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.RECIPE_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<OtherRawMaterialsCubit, OtherRawMaterialsState>(
      listenWhen: (previous, current) =>
          current.status == OtherRawMaterialsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.RECIPE_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final OtherRawMaterialsCubit cubit = context
            .read<OtherRawMaterialsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: OtherRawMaterialsTable(
            key: _tableKey,
            recipes: state.recipes,
            isLoading: state.status == OtherRawMaterialsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            onView: (recipe) =>
                RecipeRecordDialog.show(context, recipe, cubit: cubit),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.RECIPE_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.RECIPE_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_RECIPE,
                onPressed: () => RecipeFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
