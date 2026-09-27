import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../../../core/widgets/feedback/stock_update_bar.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../../data/bag_stock_repository.dart';
import '../bloc/bag_stock_cubit.dart';
import '../widgets/bag_stock_table.dart';

class BagStockView extends StatelessWidget {
  const BagStockView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();
    PackagingsService.instance.repository = ProductPackagingsRepository(
      apiClient: apiClient,
    );

    return BlocProvider<BagStockCubit>(
      create: (context) =>
          BagStockCubit(repository: BagStockRepository(apiClient: apiClient)),
      child: const _BagStockContent(),
    );
  }
}

class _BagStockContent extends StatefulWidget {
  const _BagStockContent();

  @override
  State<_BagStockContent> createState() => _BagStockContentState();
}

class _BagStockContentState extends State<_BagStockContent> {
  final GlobalKey<BagStockTableState> _tableKey =
      GlobalKey<BagStockTableState>();

  @override
  void initState() {
    super.initState();
    _primeCache();
  }

  @override
  void dispose() {
    PackagingsService.instance.reset();
    super.dispose();
  }

  Future<void> _primeCache() async {
    await PackagingsService.instance.loadPackagings(forceRefresh: true);
    if (!mounted) return;
    await context.read<BagStockCubit>().loadBagStock();
  }

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<BagStockCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onRefresh() => _primeCache();

  Future<void> _onUpdateStock() async {
    final BagStockCubit cubit = context.read<BagStockCubit>();

    if (!cubit.state.hasDraft) {
      ToastUtils.showInfo(
        context,
        AppStrings.STOCK_NOTHING_ENTERED_TITLE,
        description: AppStrings.STOCK_NOTHING_ENTERED_BODY,
      );
      return;
    }

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.STOCK_CONFIRM_TITLE,
      message: AppStrings.STOCK_CONFIRM_BODY,
      confirmLabel: AppStrings.STOCK_CONFIRM_ACTION,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.submitDraft();
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.BAG_STOCK_UPDATED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<BagStockCubit, BagStockState>(
      listenWhen: (previous, current) =>
          current.status == BagStockStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.BAG_STOCK_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final BagStockCubit cubit = context.read<BagStockCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: BagStockTable(
            key: _tableKey,
            lines: state.visibleLines,
            draftCounts: state.draftCounts,
            isLoading: state.status == BagStockStatus.loading,
            isSubmitting: state.isSubmitting,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            onCountChanged: cubit.setDraftCount,
            emptyTitle: state.isEmptySource
                ? AppStrings.BAG_STOCK_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.BAG_STOCK_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarTrailing: StockUpdateBar(
              pendingCount: state.draftCounts.length,
              isSubmitting: state.isSubmitting,
              onUpdate: _onUpdateStock,
            ),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: state.isSubmitting ? null : _onRefresh,
              ),
            ],
          ),
        );
      },
    );
  }
}
