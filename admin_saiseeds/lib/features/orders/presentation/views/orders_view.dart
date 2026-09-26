import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../../core/widgets/feedback/stock_status_chip.dart';
import '../../data/models/order_model.dart';
import '../../data/orders_repository.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../bloc/orders_cubit.dart';
import '../widgets/order_detail_dialog.dart';
import '../widgets/orders_table.dart';

class OrdersView extends StatelessWidget {
  const OrdersView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<OrdersCubit>(
      create: (context) => OrdersCubit(
        repository: OrdersRepository(apiClient: context.read<ApiClient>()),
      )..loadOrders(),
      child: const _OrdersContent(),
    );
  }
}

class _OrdersContent extends StatefulWidget {
  const _OrdersContent();

  @override
  State<_OrdersContent> createState() => _OrdersContentState();
}

class _OrdersContentState extends State<_OrdersContent> {
  final GlobalKey<OrdersTableState> _tableKey = GlobalKey<OrdersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<OrdersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  void _onView(OrderModel order) {
    OrderDetailDialog.show(
      context,
      order,
      cubit: context.read<OrdersCubit>(),
      packagingsRepository: ProductPackagingsRepository(
        apiClient: context.read<ApiClient>(),
      ),
    );
  }

  Future<void> _runAction({
    required OrderModel order,
    required String title,
    required String message,
    required String confirmLabel,
    required String successMessage,
    required Future<bool> Function(String publicId) action,
  }) async {
    final OrdersCubit cubit = context.read<OrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: title,
      message: message,
      confirmLabel: confirmLabel,
    );
    if (!confirmed) return;

    final bool succeeded = await action(order.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, successMessage);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  Future<void> _onVerify(OrderModel order) {
    final OrdersCubit cubit = context.read<OrdersCubit>();
    return _runAction(
      order: order,
      title: AppStrings.ORDER_VERIFY_TITLE,
      message: AppStrings.ORDER_VERIFY_BODY,
      confirmLabel: AppStrings.ORDER_VERIFY,
      successMessage: AppStrings.ORDER_VERIFY_DONE,
      action: cubit.verifyOrder,
    );
  }

  Future<void> _onUnverify(OrderModel order) {
    final OrdersCubit cubit = context.read<OrdersCubit>();
    return _runAction(
      order: order,
      title: AppStrings.ORDER_UNVERIFY_TITLE,
      message: AppStrings.ORDER_UNVERIFY_BODY,
      confirmLabel: AppStrings.ORDER_UNVERIFY,
      successMessage: AppStrings.ORDER_UNVERIFY_DONE,
      action: cubit.unverifyOrder,
    );
  }

  Future<void> _onHold(OrderModel order) {
    final OrdersCubit cubit = context.read<OrdersCubit>();
    return _runAction(
      order: order,
      title: AppStrings.ORDER_HOLD_TITLE,
      message: AppStrings.ORDER_HOLD_BODY,
      confirmLabel: AppStrings.ORDER_HOLD,
      successMessage: AppStrings.ORDER_HOLD_DONE,
      action: cubit.holdOrder,
    );
  }

  Future<void> _onReject(OrderModel order) {
    final OrdersCubit cubit = context.read<OrdersCubit>();
    return _runAction(
      order: order,
      title: AppStrings.ORDER_REJECT_TITLE,
      message: AppStrings.ORDER_REJECT_BODY,
      confirmLabel: AppStrings.ORDER_REJECT,
      successMessage: AppStrings.ORDER_REJECT_DONE,
      action: cubit.rejectOrder,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<OrdersCubit, OrdersState>(
      listenWhen: (previous, current) =>
          current.status == OrdersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.ORDERS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final OrdersCubit cubit = context.read<OrdersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: OrdersTable(
            key: _tableKey,
            orders: state.orders,
            isLoading: state.status == OrdersStatus.loading,
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
            onView: _onView,
            onVerify: _onVerify,
            onUnverify: _onUnverify,
            onHold: _onHold,
            onReject: _onReject,
            searchBarTrailing: StockStatusChip(
              isComplete: state.isTodaysStockComplete,
            ),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
            ],
          ),
        );
      },
    );
  }
}
