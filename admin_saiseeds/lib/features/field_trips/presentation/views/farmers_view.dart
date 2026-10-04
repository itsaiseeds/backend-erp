import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../data/field_trips_repository.dart';
import '../bloc/farmers_cubit.dart';
import '../widgets/farmer_detail_dialog.dart';
import '../widgets/farmers_table.dart';

class FarmersView extends StatelessWidget {
  const FarmersView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<FarmersCubit>(
      create: (context) => FarmersCubit(
        repository: FieldTripsRepository(apiClient: context.read<ApiClient>()),
      )..loadFarmers(),
      child: const _FarmersContent(),
    );
  }
}

class _FarmersContent extends StatelessWidget {
  const _FarmersContent();

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<FarmersCubit, FarmersState>(
      listenWhen: (previous, current) =>
          current.status == FarmersStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.FARMERS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final FarmersCubit cubit = context.read<FarmersCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: FarmersTable(
            farmers: state.farmers,
            isLoading: state.status == FarmersStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData:
                ({
                  required int page,
                  required int limit,
                  String? search,
                  String? sortBy,
                  String? sortOrder,
                  Map<String, String>? filters,
                }) => cubit.applyQuery(
                  page: page,
                  limit: limit,
                  search: search,
                  sortBy: sortBy,
                  sortOrder: sortOrder,
                  filters: filters,
                ),
            hasMore: state.hasMore,
            onLoadMore: cubit.loadMore,
            onView: (farmer) =>
                FarmerDetailDialog.show(context, farmer: farmer),
            emptyTitle: state.isEmptySource
                ? AppStrings.FARMERS_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.FARMERS_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
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
