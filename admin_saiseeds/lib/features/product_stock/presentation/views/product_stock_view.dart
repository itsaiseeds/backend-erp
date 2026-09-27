import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/stock_as_of_chip.dart';
import '../../data/product_stock_repository.dart';
import '../bloc/product_stock_cubit.dart';
import '../widgets/product_stock_table.dart';

class ProductStockView extends StatelessWidget {
  const ProductStockView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<ProductStockCubit>(
      create: (context) => ProductStockCubit(
        repository: ProductStockRepository(apiClient: apiClient),
      )..loadProductStock(),
      child: const _ProductStockContent(),
    );
  }
}

class _ProductStockContent extends StatefulWidget {
  const _ProductStockContent();

  @override
  State<_ProductStockContent> createState() => _ProductStockContentState();
}

class _ProductStockContentState extends State<_ProductStockContent> {
  final GlobalKey<ProductStockTableState> _tableKey =
      GlobalKey<ProductStockTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<ProductStockCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ProductStockCubit, ProductStockState>(
      listenWhen: (previous, current) =>
          current.status == ProductStockStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.PRODUCT_STOCK_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final ProductStockCubit cubit = context.read<ProductStockCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: ProductStockTable(
            key: _tableKey,
            lines: state.visibleLines,
            isLoading: state.status == ProductStockStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            emptyTitle: state.isEmptySource
                ? AppStrings.PRODUCT_STOCK_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.PRODUCT_STOCK_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarTrailing: StockAsOfChip(isoDate: state.snapshotDate),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadProductStock,
              ),
            ],
          ),
        );
      },
    );
  }
}
