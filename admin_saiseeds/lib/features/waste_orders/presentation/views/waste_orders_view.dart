import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../products/data/products_repository.dart';
import '../../data/waste_orders_repository.dart';
import '../../../custom_orders/data/models/custom_order_model.dart';
import '../bloc/waste_orders_cubit.dart';
import '../widgets/waste_order_detail_dialog.dart';
import '../widgets/waste_order_dispatch_dialog.dart';
import '../widgets/waste_order_form_dialog.dart';
import '../widgets/waste_orders_table.dart';

class WasteOrdersView extends StatelessWidget {
  const WasteOrdersView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );

    return BlocProvider<WasteOrdersCubit>(
      create: (context) => WasteOrdersCubit(
        repository: WasteOrdersRepository(apiClient: apiClient),
      )..loadWasteOrders(),
      child: const _WasteOrdersContent(),
    );
  }
}

class _WasteOrdersContent extends StatefulWidget {
  const _WasteOrdersContent();

  @override
  State<_WasteOrdersContent> createState() => _WasteOrdersContentState();
}

class _WasteOrdersContentState extends State<_WasteOrdersContent> {
  final GlobalKey<WasteOrdersTableState> _tableKey =
      GlobalKey<WasteOrdersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<WasteOrdersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onCreate() async {
    await WasteOrderFormDialog.show(
      context,
      cubit: context.read<WasteOrdersCubit>(),
    );
  }

  Future<void> _onView(CustomOrderModel order) async {
    final WasteOrdersCubit cubit = context.read<WasteOrdersCubit>();
    final CustomOrderModel? full = await cubit.fetchWasteOrder(order.publicId);
    if (!mounted) return;

    await WasteOrderDetailDialog.show(
      context,
      cubit: cubit,
      order: full ?? order,
    );
  }

  Future<void> _onDelete(CustomOrderModel order) async {
    final WasteOrdersCubit cubit = context.read<WasteOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.WASTE_ORDER_DELETE_TITLE,
      message: '${order.publicId} - ${AppStrings.WASTE_ORDER_DELETE_BODY}',
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteWasteOrder(order.publicId);
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
    final WasteOrdersCubit cubit = context.read<WasteOrdersCubit>();
    // The list payload carries no lines, but the dispatch form needs one lot
    // number per line, so the full order is pulled first.
    final CustomOrderModel? full = await cubit.fetchWasteOrder(order.publicId);
    if (!mounted) return;

    await WasteOrderDispatchDialog.show(
      context,
      cubit: cubit,
      order: full ?? order,
    );
  }

  Future<void> _onRevertDispatch(CustomOrderModel order) async {
    final WasteOrdersCubit cubit = context.read<WasteOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.ORDER_REVERT_DISPATCH_TITLE,
      message:
          '${order.publicId} - '
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
    return BlocConsumer<WasteOrdersCubit, WasteOrdersState>(
      listenWhen: (previous, current) =>
          current.status == WasteOrdersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.CUSTOM_ORDER_LOAD_FAILED,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final WasteOrdersCubit cubit = context.read<WasteOrdersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: WasteOrdersTable(
            key: _tableKey,
            orders: state.orders,
            isLoading: state.status == WasteOrdersStatus.loading,
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
                tooltip: AppStrings.WASTE_ORDER_ADD,
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
