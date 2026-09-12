import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/confirmation_dialog.dart';
import '../../data/clients_repository.dart';
import '../../data/models/client_model.dart';
import '../bloc/clients_cubit.dart';
import '../widgets/client_detail_dialog.dart';
import '../widgets/client_form_dialog.dart';
import '../widgets/clients_table.dart';
import '../widgets/clients_view_switcher.dart';

class ClientsView extends StatelessWidget {
  const ClientsView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<ClientsCubit>(
      create: (context) => ClientsCubit(
        repository: ClientsRepository(apiClient: context.read<ApiClient>()),
      )..loadClients(),
      child: const _ClientsContent(),
    );
  }
}

class _ClientsContent extends StatefulWidget {
  const _ClientsContent();

  @override
  State<_ClientsContent> createState() => _ClientsContentState();
}

class _ClientsContentState extends State<_ClientsContent> {
  final GlobalKey<ClientsTableState> _tableKey = GlobalKey<ClientsTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<ClientsCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  Future<void> _onAccept(ClientModel client) async {
    final ClientsCubit cubit = context.read<ClientsCubit>();

    final bool confirmed = await ConfirmationDialog.show(
      context,
      title: AppStrings.CLIENT_ACCEPT_TITLE,
      message: AppStrings.CLIENT_ACCEPT_BODY,
      confirmLabel: AppStrings.CLIENT_ACCEPT,
    );
    if (!confirmed) return;

    final bool succeeded = await cubit.verifyClient(client.publicId);
    if (!mounted) return;

    if (succeeded) {
      ToastUtils.showSuccess(context, AppStrings.CLIENT_ACCEPTED_TITLE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  Future<void> _onView(ClientModel client) async {
    final ClientsCubit cubit = context.read<ClientsCubit>();
    final ClientModel? detail = await cubit.fetchClient(client.publicId);
    if (!mounted) return;

    ClientDetailDialog.show(context, detail ?? client);
  }

  Future<void> _onEdit(ClientModel client) async {
    final ClientsCubit cubit = context.read<ClientsCubit>();
    final ClientModel? detail = await cubit.fetchClient(client.publicId);
    if (!mounted) return;

    ClientFormDialog.show(context, cubit: cubit, client: detail ?? client);
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<ClientsCubit, ClientsState>(
      listenWhen: (previous, current) =>
          current.status == ClientsStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.CLIENTS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final ClientsCubit cubit = context.read<ClientsCubit>();
        final bool isPending = state.view == ClientsViewMode.pending;

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: SizedBox(
                  width: AppSizes.clientSwitcherWidth,
                  child: ClientsViewSwitcher(
                    selected: state.view,
                    onChanged: cubit.selectView,
                  ),
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Expanded(
                child: ClientsTable(
                  key: _tableKey,
                  clients: state.clients,
                  isLoading: state.status == ClientsStatus.loading,
                  isPendingView: isPending,
                  currentPage: state.currentPage,
                  totalPages: state.totalPages,
                  totalItems: state.totalItems,
                  currentSortBy: state.sortBy,
                  currentSortOrder: state.sortOrder,
                  currentFilters: state.filters,
                  availableFilters: state.availableFilters,
                  availableSorts: state.availableSorts,
                  onFetchData: _onFetchData,
                  onView: _onView,
                  onEdit: _onEdit,
                  onAccept: isPending ? _onAccept : null,
                  emptyTitle: isPending
                      ? AppStrings.CLIENTS_PENDING_EMPTY_TITLE
                      : AppStrings.CLIENTS_EMPTY_STATE_TITLE,
                  emptyDescription: isPending
                      ? AppStrings.CLIENTS_PENDING_EMPTY_BODY
                      : AppStrings.CLIENTS_EMPTY_STATE_BODY,
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
