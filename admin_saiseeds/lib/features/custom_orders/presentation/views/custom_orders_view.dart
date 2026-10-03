import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../../../products/data/products_repository.dart';
import '../../data/custom_orders_repository.dart';
import '../../data/models/custom_order_model.dart';
import '../bloc/custom_orders_cubit.dart';
import '../widgets/custom_order_detail_dialog.dart';
import '../widgets/custom_order_dispatch_dialog.dart';
import '../widgets/custom_order_form_dialog.dart';
import '../widgets/custom_orders_table.dart';

class CustomOrdersView extends StatelessWidget {
  const CustomOrdersView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );
    PackagingsService.instance.repository = ProductPackagingsRepository(
      apiClient: apiClient,
    );

    return BlocProvider<CustomOrdersCubit>(
      create: (context) => CustomOrdersCubit(
        repository: CustomOrdersRepository(apiClient: apiClient),
      )..loadCustomOrders(),
      child: const _CustomOrdersContent(),
    );
  }
}

class _CustomOrdersContent extends StatefulWidget {
  const _CustomOrdersContent();

  @override
  State<_CustomOrdersContent> createState() => _CustomOrdersContentState();
}

class _CustomOrdersContentState extends State<_CustomOrdersContent> {
  final GlobalKey<CustomOrdersTableState> _tableKey =
      GlobalKey<CustomOrdersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<CustomOrdersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onCreate() async {
    await CustomOrderFormDialog.show(
      context,
      cubit: context.read<CustomOrdersCubit>(),
    );
  }

  Future<void> _onView(CustomOrderModel order) async {
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();
    final CustomOrderModel? full = await cubit.fetchCustomOrder(
      order.publicId,
    );
    if (!mounted) return;

    await CustomOrderDetailDialog.show(
      context,
      cubit: cubit,
      order: full ?? order,
    );
  }

  Future<void> _onDelete(CustomOrderModel order) async {
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.CUSTOM_ORDER_DELETE_TITLE,
      message: '${order.publicId} - ${AppStrings.CUSTOM_ORDER_DELETE_BODY}',
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteCustomOrder(order.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.CUSTOM_ORDER_DELETED);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  Future<void> _onDispatch(CustomOrderModel order) async {
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();
    // The list payload carries no lines, but the dispatch form needs one lot
    // number per line, so the full order is pulled first.
    final CustomOrderModel? full = await cubit.fetchCustomOrder(
      order.publicId,
    );
    if (!mounted) return;

    await CustomOrderDispatchDialog.show(
      context,
      cubit: cubit,
      order: full ?? order,
    );
  }

  Future<void> _onRevertDispatch(CustomOrderModel order) async {
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.ORDER_REVERT_DISPATCH_TITLE,
      message: '${order.publicId} - '
          '${AppStrings.ORDER_REVERT_DISPATCH_BODY}',
      confirmLabel: AppStrings.ORDER_REVERT_DISPATCH,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.revertDispatch(order.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.ORDER_REVERT_DISPATCH_DONE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<CustomOrdersCubit, CustomOrdersState>(
      listenWhen: (previous, current) =>
          current.status == CustomOrdersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.CUSTOM_ORDER_LOAD_FAILED,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: CustomOrdersTable(
            key: _tableKey,
            orders: state.orders,
            isLoading: state.status == CustomOrdersStatus.loading,
            isMutating: state.isMutating,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: _onView,
            onDelete: _onDelete,
            onDispatch: _onDispatch,
            onRevertDispatch: _onRevertDispatch,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              IconActionButton(
                expand: true,
                icon: Icons.add_rounded,
                tooltip: AppStrings.CUSTOM_ORDER_ADD,
                type: IconActionType.primary,
                onPressed: _onCreate,
              ),
            ],
          ),
        );
      },
    );
  }
}
