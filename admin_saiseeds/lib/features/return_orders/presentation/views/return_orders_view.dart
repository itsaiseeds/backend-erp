import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/models/return_order_model.dart';
import '../../data/return_orders_repository.dart';
import '../bloc/return_orders_cubit.dart';
import '../widgets/return_order_accept_dialog.dart';
import '../widgets/return_order_detail_dialog.dart';
import '../widgets/return_order_edit_dialog.dart';
import '../widgets/return_order_slip_dialog.dart';
import '../widgets/return_orders_table.dart';

class ReturnOrdersView extends StatelessWidget {
  const ReturnOrdersView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<ReturnOrdersCubit>(
      create: (context) => ReturnOrdersCubit(
        repository: ReturnOrdersRepository(
          apiClient: context.read<ApiClient>(),
        ),
      )..loadReturnOrders(),
      child: const _ReturnOrdersContent(),
    );
  }
}

class _ReturnOrdersContent extends StatefulWidget {
  const _ReturnOrdersContent();

  @override
  State<_ReturnOrdersContent> createState() => _ReturnOrdersContentState();
}

class _ReturnOrdersContentState extends State<_ReturnOrdersContent> {
  final GlobalKey<ReturnOrdersTableState> _tableKey =
      GlobalKey<ReturnOrdersTableState>();

  ReturnOrdersRepository get _repository =>
      ReturnOrdersRepository(apiClient: context.read<ApiClient>());

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<ReturnOrdersCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onView(ReturnOrderModel returnOrder) async {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();
    final bool saved = await ReturnOrderDetailDialog.show(
      context,
      returnOrder,
      repository: _repository,
    );

    // The dialog calls the repository itself so its own submit state is real,
    // so the queue is refreshed here rather than through the cubit's path.
    if (saved) await cubit.refresh();

    if (!saved || !mounted) return;
    ToastUtils.showSuccess(context, AppStrings.RETURN_ORDER_EDIT_DONE);
  }

  Future<void> _onViewSlip(ReturnOrderModel returnOrder) {
    return ReturnOrderSlipDialog.show(
      context,
      returnOrder: returnOrder,
      apiClient: context.read<ApiClient>(),
    );
  }

  Future<void> _onEdit(ReturnOrderModel returnOrder) async {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();
    final bool saved = await ReturnOrderEditDialog.show(
      context,
      returnOrder: returnOrder,
      repository: _repository,
    );

    if (saved) await cubit.refresh();

    if (!saved || !mounted) return;
    ToastUtils.showSuccess(context, AppStrings.RETURN_ORDER_EDIT_DONE);
  }

  /// Accepting is the one verb that is not a plain confirmation: it needs the
  /// recipe picks, so it opens its own dialog rather than a yes/no prompt.
  Future<void> _onAccept(ReturnOrderModel returnOrder) async {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();

    final bool accepted = await ReturnOrderAcceptDialog.show(
      context,
      returnOrder: returnOrder,
      repository: _repository,
      loadRecipes: cubit.fetchRecipes,
    );

    // The dialog calls the repository itself so its own submit state is real, so
    // the queue is refreshed here rather than through the cubit's mutation path.
    await cubit.refresh();

    if (!accepted || !mounted) return;
    ToastUtils.showSuccess(context, AppStrings.RETURN_ORDER_ACCEPT_DONE);
  }

  Future<void> _runAction({
    required ReturnOrderModel returnOrder,
    required String title,
    required String message,
    required String confirmLabel,
    required String successMessage,
    required Future<bool> Function(String publicId) action,
  }) async {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: title,
      message: message,
      confirmLabel: confirmLabel,
    );
    if (!confirmed) return;

    final bool succeeded = await action(returnOrder.publicId);
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

  Future<void> _onReject(ReturnOrderModel returnOrder) {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();
    return _runAction(
      returnOrder: returnOrder,
      title: AppStrings.RETURN_ORDER_REJECT_TITLE,
      message: AppStrings.RETURN_ORDER_REJECT_BODY,
      confirmLabel: AppStrings.RETURN_ORDER_REJECT,
      successMessage: AppStrings.RETURN_ORDER_REJECT_DONE,
      action: cubit.rejectReturn,
    );
  }

  Future<void> _onUnreject(ReturnOrderModel returnOrder) {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();
    return _runAction(
      returnOrder: returnOrder,
      title: AppStrings.RETURN_ORDER_UNREJECT_TITLE,
      message: AppStrings.RETURN_ORDER_UNREJECT_BODY,
      confirmLabel: AppStrings.RETURN_ORDER_UNREJECT,
      successMessage: AppStrings.RETURN_ORDER_UNREJECT_DONE,
      action: cubit.unrejectReturn,
    );
  }

  Future<void> _onRevertAccept(ReturnOrderModel returnOrder) {
    final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();
    return _runAction(
      returnOrder: returnOrder,
      title: AppStrings.RETURN_ORDER_REVERT_ACCEPT_TITLE,
      message: AppStrings.RETURN_ORDER_REVERT_ACCEPT_BODY,
      confirmLabel: AppStrings.RETURN_ORDER_REVERT_ACCEPT,
      successMessage: AppStrings.RETURN_ORDER_REVERT_ACCEPT_DONE,
      action: cubit.revertAcceptReturn,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ReturnOrdersCubit, ReturnOrdersState>(
      listenWhen: (previous, current) =>
          current.status == ReturnOrdersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.RETURN_ORDERS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final ReturnOrdersCubit cubit = context.read<ReturnOrdersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: ReturnOrdersTable(
            key: _tableKey,
            returnOrders: state.returnOrders,
            isLoading: state.status == ReturnOrdersStatus.loading,
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
            onViewSlip: _onViewSlip,
            onEdit: _onEdit,
            onAccept: _onAccept,
            onReject: _onReject,
            onUnreject: _onUnreject,
            onRevertAccept: _onRevertAccept,
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
