import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/stock_as_of_chip.dart';
import '../../data/other_material_stock_repository.dart';
import '../bloc/other_material_stock_cubit.dart';
import '../widgets/other_material_stock_table.dart';

class OtherMaterialStockView extends StatelessWidget {
  const OtherMaterialStockView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<OtherMaterialStockCubit>(
      create: (context) => OtherMaterialStockCubit(
        repository: OtherMaterialStockRepository(apiClient: apiClient),
      )..loadOtherMaterialStock(),
      child: const _OtherMaterialStockContent(),
    );
  }
}

class _OtherMaterialStockContent extends StatefulWidget {
  const _OtherMaterialStockContent();

  @override
  State<_OtherMaterialStockContent> createState() =>
      _OtherMaterialStockContentState();
}

class _OtherMaterialStockContentState
    extends State<_OtherMaterialStockContent> {
  final GlobalKey<OtherMaterialStockTableState> _tableKey =
      GlobalKey<OtherMaterialStockTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<OtherMaterialStockCubit>().applyQuery(
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
    return BlocConsumer<OtherMaterialStockCubit, OtherMaterialStockState>(
      listenWhen: (previous, current) =>
          current.status == OtherMaterialStockStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.OTHER_MATERIAL_STOCK_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final OtherMaterialStockCubit cubit = context
            .read<OtherMaterialStockCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: OtherMaterialStockTable(
            key: _tableKey,
            lines: state.visibleLines,
            isLoading: state.status == OtherMaterialStockStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            onFetchData: _onFetchData,
            emptyTitle: state.isEmptySource
                ? AppStrings.OTHER_MATERIAL_STOCK_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.OTHER_MATERIAL_STOCK_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarTrailing: StockAsOfChip(isoDate: state.asOf),
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.loadOtherMaterialStock,
              ),
            ],
          ),
        );
      },
    );
  }
}
