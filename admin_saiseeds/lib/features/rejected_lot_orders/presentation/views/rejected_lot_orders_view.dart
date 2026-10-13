import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../custom_orders/data/models/custom_order_model.dart';
import '../../data/rejected_lot_orders_repository.dart';
import '../bloc/rejected_lot_orders_cubit.dart';
import '../widgets/rejected_lot_order_detail_dialog.dart';
import '../widgets/rejected_lot_order_form_dialog.dart';
import '../widgets/rejected_lot_orders_table.dart';

class RejectedLotOrdersView extends StatelessWidget {
  const RejectedLotOrdersView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<RejectedLotOrdersCubit>(
      create: (context) => RejectedLotOrdersCubit(
        repository: RejectedLotOrdersRepository(apiClient: apiClient),
      )..loadRejectedOrders(),
      child: const _RejectedLotOrdersContent(),
    );
  }
}

class _RejectedLotOrdersContent extends StatefulWidget {
  const _RejectedLotOrdersContent();

  @override
  State<_RejectedLotOrdersContent> createState() =>
      _RejectedLotOrdersContentState();
}

class _RejectedLotOrdersContentState extends State<_RejectedLotOrdersContent> {
  final GlobalKey<RejectedLotOrdersTableState> _tableKey =
      GlobalKey<RejectedLotOrdersTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<RejectedLotOrdersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onCreate() async {
    await RejectedLotOrderFormDialog.show(
      context,
      cubit: context.read<RejectedLotOrdersCubit>(),
    );
  }

  Future<void> _onView(CustomOrderModel order) async {
    final RejectedLotOrdersCubit cubit = context.read<RejectedLotOrdersCubit>();
    final CustomOrderModel? full = await cubit.fetchRejectedOrder(
      order.publicId,
    );
    if (!mounted) return;

    await RejectedLotOrderDetailDialog.show(context, order: full ?? order);
  }

  Future<void> _onDelete(CustomOrderModel order) async {
    final RejectedLotOrdersCubit cubit = context.read<RejectedLotOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.REJECTED_LOT_ORDER_DELETE_TITLE,
      message:
          '${order.publicId} - ${AppStrings.REJECTED_LOT_ORDER_DELETE_BODY}',
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteRejectedOrder(order.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.REJECTED_LOT_ORDER_DELETED);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<RejectedLotOrdersCubit, RejectedLotOrdersState>(
      listenWhen: (previous, current) =>
          current.status == RejectedLotOrdersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.REJECTED_LOT_ORDER_LOAD_FAILED,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final RejectedLotOrdersCubit cubit = context
            .read<RejectedLotOrdersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: RejectedLotOrdersTable(
            key: _tableKey,
            orders: state.orders,
            isLoading: state.status == RejectedLotOrdersStatus.loading,
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
                tooltip: AppStrings.REJECTED_LOT_ORDER_ADD,
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
