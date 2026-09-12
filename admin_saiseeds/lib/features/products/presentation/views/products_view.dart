import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/crops_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/crops_repository.dart';
import '../../data/models/product_model.dart';
import '../../data/products_repository.dart';
import '../bloc/products_cubit.dart';
import '../widgets/product_detail_dialog.dart';
import '../widgets/product_form_dialog.dart';
import '../widgets/products_table.dart';

class ProductsView extends StatelessWidget {
  const ProductsView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    CropsService.instance.repository = CropsRepository(apiClient: apiClient);

    return BlocProvider<ProductsCubit>(
      create: (context) =>
          ProductsCubit(repository: ProductsRepository(apiClient: apiClient))
            ..loadProducts(),
      child: const _ProductsContent(),
    );
  }
}

class _ProductsContent extends StatefulWidget {
  const _ProductsContent();

  @override
  State<_ProductsContent> createState() => _ProductsContentState();
}

class _ProductsContentState extends State<_ProductsContent> {
  final GlobalKey<ProductsTableState> _tableKey =
      GlobalKey<ProductsTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<ProductsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(ProductModel product) async {
    final ProductsCubit cubit = context.read<ProductsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_PRODUCT_TITLE,
      message: AppStrings.DELETE_PRODUCT_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteProduct(product.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.PRODUCT_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ProductsCubit, ProductsState>(
      listenWhen: (previous, current) =>
          current.status == ProductsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.PRODUCTS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final ProductsCubit cubit = context.read<ProductsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: ProductsTable(
            key: _tableKey,
            products: state.visibleProducts,
            isLoading: state.status == ProductsStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onView: (product) => ProductDetailDialog.show(context, product),
            onEdit: (product) =>
                ProductFormDialog.show(context, cubit: cubit, product: product),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.PRODUCTS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.PRODUCTS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadProducts,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_PRODUCT,
                onPressed: () => ProductFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
