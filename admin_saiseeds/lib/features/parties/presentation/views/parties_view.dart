import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/add_action_button.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/models/party_model.dart';
import '../../data/parties_repository.dart';
import '../bloc/parties_cubit.dart';
import '../widgets/parties_table.dart';
import '../widgets/party_form_dialog.dart';
import '../widgets/party_record_dialog.dart';

class PartiesView extends StatelessWidget {
  const PartiesView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<PartiesCubit>(
      create: (context) => PartiesCubit(
        repository: PartiesRepository(apiClient: context.read<ApiClient>()),
      )..loadParties(),
      child: const _PartiesContent(),
    );
  }
}

class _PartiesContent extends StatefulWidget {
  const _PartiesContent();

  @override
  State<_PartiesContent> createState() => _PartiesContentState();
}

class _PartiesContentState extends State<_PartiesContent> {
  final GlobalKey<PartiesTableState> _tableKey =
      GlobalKey<PartiesTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<PartiesCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onDelete(PartyModel party) async {
    final PartiesCubit cubit = context.read<PartiesCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.DELETE_PARTY_TITLE,
      message: AppStrings.DELETE_PARTY_BODY,
      confirmLabel: AppStrings.DELETE,
      isDangerous: true,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.deleteParty(party.id);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.PARTY_DELETED_TITLE);
      return;
    }
    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<PartiesCubit, PartiesState>(
      listenWhen: (previous, current) =>
          current.status == PartiesStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.PARTIES_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final PartiesCubit cubit = context.read<PartiesCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: PartiesTable(
            key: _tableKey,
            parties: state.parties,
            isLoading: state.status == PartiesStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            onView: (party) =>
                PartyRecordDialog.show(context, party, cubit: cubit),
            onDelete: _onDelete,
            emptyTitle: state.isEmptySource
                ? AppStrings.PARTIES_EMPTY_STATE_TITLE
                : AppStrings.TABLE_EMPTY_TITLE,
            emptyDescription: state.isEmptySource
                ? AppStrings.PARTIES_EMPTY_STATE_BODY
                : AppStrings.TABLE_EMPTY_BODY,
            searchBarActions: [
              IconActionButton(
                expand: true,
                icon: Icons.refresh_rounded,
                tooltip: AppStrings.TABLE_REFRESH,
                onPressed: cubit.refresh,
              ),
              AddActionButton(
                tooltip: AppStrings.ADD_PARTY,
                onPressed: () => PartyFormDialog.show(context, cubit: cubit),
              ),
            ],
          ),
        );
      },
    );
  }
}
