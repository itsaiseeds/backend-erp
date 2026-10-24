import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../data/sales_people_repository.dart';
import '../bloc/old_sales_people_cubit.dart';
import '../widgets/old_sales_people_table.dart';

class OldSalesPeopleView extends StatelessWidget {
  const OldSalesPeopleView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<OldSalesPeopleCubit>(
      create: (context) => OldSalesPeopleCubit(
        repository: SalesPeopleRepository(apiClient: context.read<ApiClient>()),
      )..loadOldSalesPeople(),
      child: const _OldSalesPeopleContent(),
    );
  }
}

class _OldSalesPeopleContent extends StatefulWidget {
  const _OldSalesPeopleContent();

  @override
  State<_OldSalesPeopleContent> createState() =>
      _OldSalesPeopleContentState();
}

class _OldSalesPeopleContentState extends State<_OldSalesPeopleContent> {
  final GlobalKey<OldSalesPeopleTableState> _tableKey =
      GlobalKey<OldSalesPeopleTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<OldSalesPeopleCubit>().applyQuery(
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
    return BlocConsumer<OldSalesPeopleCubit, OldSalesPeopleState>(
      listenWhen: (previous, current) =>
          current.status == OldSalesPeopleStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.OLD_SALES_PEOPLE_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final OldSalesPeopleCubit cubit = context.read<OldSalesPeopleCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: OldSalesPeopleTable(
                  key: _tableKey,
                  salesPeople: state.visibleSalesPeople,
                  isLoading: state.status == OldSalesPeopleStatus.loading,
                  currentPage: state.currentPage,
                  totalPages: state.totalPages,
                  totalItems: state.totalItems,
                  currentSortBy: state.sortBy,
                  currentSortOrder: state.sortOrder,
                  onFetchData: _onFetchData,
                  searchBarActions: [
                    IconActionButton(
                      expand: true,
                      icon: Icons.refresh_rounded,
                      tooltip: AppStrings.TABLE_REFRESH,
                      onPressed: cubit.refresh,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
