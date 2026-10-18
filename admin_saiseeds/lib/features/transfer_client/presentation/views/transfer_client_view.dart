import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../sales_people/data/sales_people_repository.dart';
import '../bloc/transfer_client_cubit.dart';
import '../widgets/sales_person_filter_dropdown.dart';
import '../widgets/transfer_client_dialog.dart';
import '../widgets/transfer_client_table.dart';

class TransferClientView extends StatelessWidget {
  const TransferClientView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<TransferClientCubit>(
      create: (context) => TransferClientCubit(
        repository: SalesPeopleRepository(apiClient: context.read<ApiClient>()),
      )..loadSourceOptions(),
      child: const _TransferClientContent(),
    );
  }
}

class _TransferClientContent extends StatefulWidget {
  const _TransferClientContent();

  @override
  State<_TransferClientContent> createState() =>
      _TransferClientContentState();
}

class _TransferClientContentState extends State<_TransferClientContent> {
  final GlobalKey<TransferClientTableState> _tableKey =
      GlobalKey<TransferClientTableState>();

  Map<String, String> _selection = const {};

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<TransferClientCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  void _onSelectionChanged(Map<String, String> selection) {
    setState(() => _selection = selection);
  }

  Future<void> _onTransfer() async {
    final TransferClientCubit cubit = context.read<TransferClientCubit>();

    final bool? succeeded = await TransferClientDialog.show(
      context,
      cubit: cubit,
      clientIds: _selection.keys.toList(),
      clientLabels: _selection.values.toList(),
    );

    if (succeeded == true && mounted) {
      _tableKey.currentState?.clearSelection();
      setState(() => _selection = const {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<TransferClientCubit, TransferClientState>(
      listenWhen: (previous, current) =>
          current.status == TransferClientStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.TRANSFER_CLIENT_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final TransferClientCubit cubit = context.read<TransferClientCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: TransferClientTable(
                  key: _tableKey,
                  clients: state.clients,
                  isLoading: state.status == TransferClientStatus.loading,
                  hasSource: state.hasSource,
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
                  onSelectionChanged: _onSelectionChanged,
                  searchBarTrailing: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SalesPersonFilterDropdown(
                        options: state.sourceOptions,
                        value: state.sourceSalesPerson,
                        onChanged: (person) => cubit.selectSource(person),
                      ),
                      const SizedBox(width: AppSpacing.smd),
                      _TransferButton(
                        count: _selection.length,
                        onPressed: _selection.isEmpty ? null : _onTransfer,
                      ),
                    ],
                  ),
                  searchBarActions: [
                    IconActionButton(
                      expand: true,
                      icon: Icons.refresh_rounded,
                      tooltip: AppStrings.TABLE_REFRESH,
                      onPressed: state.hasSource ? cubit.refresh : null,
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

class _TransferButton extends StatelessWidget {
  final int count;
  final VoidCallback? onPressed;

  const _TransferButton({required this.count, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    final String label = count > 0
        ? '${AppStrings.TRANSFER_CLIENT_ACTION} ($count)'
        : AppStrings.TRANSFER_CLIENT_ACTION;

    return PrimaryButton(
      label: label,
      icon: Icons.swap_horizontal_circle_outlined,
      onPressed: onPressed,
    );
  }
}
