import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/stock_as_of_chip.dart';
import '../../data/raw_material_stock_repository.dart';
import '../bloc/raw_material_stock_cubit.dart';
import '../widgets/raw_material_stock_table.dart';

class RawMaterialStockView extends StatelessWidget {
  const RawMaterialStockView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<RawMaterialStockCubit>(
      create: (context) => RawMaterialStockCubit(
        repository: RawMaterialStockRepository(apiClient: apiClient),
      )..loadRawMaterialStock(),
      child: const _RawMaterialStockContent(),
    );
  }
}

class _RawMaterialStockContent extends StatefulWidget {
  const _RawMaterialStockContent();

  @override
  State<_RawMaterialStockContent> createState() =>
      _RawMaterialStockContentState();
}

class _RawMaterialStockContentState extends State<_RawMaterialStockContent> {
  final GlobalKey<RawMaterialStockTableState> _tableKey =
      GlobalKey<RawMaterialStockTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<RawMaterialStockCubit>().applyQuery(
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
    return BlocConsumer<RawMaterialStockCubit, RawMaterialStockState>(
      listenWhen: (previous, current) =>
          current.status == RawMaterialStockStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.RAW_MATERIAL_STOCK_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final RawMaterialStockCubit cubit = context
            .read<RawMaterialStockCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: RawMaterialStockTable(
            key: _tableKey,
            lines: state.visibleLines,
            isLoading: state.status == RawMaterialStockStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            emptyTitle: state.isEmptySource
                ? AppStrings.RAW_MATERIAL_STOCK_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.RAW_MATERIAL_STOCK_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarTrailing: StockAsOfChip(isoDate: state.asOf),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadRawMaterialStock,
              ),
            ],
          ),
        );
      },
    );
  }
}
