import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../products/data/products_repository.dart';
import '../../data/models/product_packaging_model.dart';
import '../../data/product_packagings_repository.dart';
import '../bloc/product_packagings_cubit.dart';
import '../widgets/product_packaging_detail_dialog.dart';
import '../widgets/product_packaging_form_dialog.dart';
import '../widgets/product_packagings_table.dart';

class ProductPackagingsView extends StatelessWidget {
  const ProductPackagingsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );
    ProductsService.instance.loadProducts();

    return BlocProvider<ProductPackagingsCubit>(
      create: (context) => ProductPackagingsCubit(
        repository: ProductPackagingsRepository(apiClient: apiClient),
      )..loadProductPackagings(),
      child: const _ProductPackagingsContent(),
    );
  }
}

class _ProductPackagingsContent extends StatefulWidget {
  const _ProductPackagingsContent();

  @override
  State<_ProductPackagingsContent> createState() =>
      _ProductPackagingsContentState();
}

class _ProductPackagingsContentState extends State<_ProductPackagingsContent> {
  final GlobalKey<ProductPackagingsTableState> _tableKey =
      GlobalKey<ProductPackagingsTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<ProductPackagingsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(ProductPackagingModel packaging) async {
    final ProductPackagingsCubit cubit = context.read<ProductPackagingsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_PRODUCT_PACKAGING_TITLE,
      message: AppStrings.DELETE_PRODUCT_PACKAGING_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteProductPackaging(
      packaging.publicId,
    );
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(
        context,
        AppStrings.PRODUCT_PACKAGING_DELETED_TITLE,
      );
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  Future<void> _onRefresh() async {
    final ProductPackagingsCubit cubit = context.read<ProductPackagingsCubit>();
    await ProductsService.instance.loadProducts(forceRefresh: true);
    await cubit.loadProductPackagings();
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ProductPackagingsCubit, ProductPackagingsState>(
      listenWhen: (previous, current) =>
          current.status == ProductPackagingsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.PRODUCT_PACKAGINGS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final ProductPackagingsCubit cubit = context
            .read<ProductPackagingsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: ProductPackagingsTable(
            key: _tableKey,
            packagings: state.visiblePackagings,
            isLoading: state.status == ProductPackagingsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (packaging) =>
                ProductPackagingDetailDialog.show(context, packaging),
            onEdit: (packaging) => ProductPackagingFormDialog.show(
              context,
              cubit: cubit,
              packaging: packaging,
            ),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.PRODUCT_PACKAGINGS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.PRODUCT_PACKAGINGS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: _onRefresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_PRODUCT_PACKAGING,
                onPressed: () =>
                    ProductPackagingFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
