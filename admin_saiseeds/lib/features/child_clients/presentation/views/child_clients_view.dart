import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_filter_search_bar.dart';
import '../../../../core/widgets/tables/app_data_column.dart';
import '../../../../core/widgets/tables/app_data_table.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/client_model.dart';
import '../../../clients/data/models/client_status.dart';
import '../../../orders/data/models/child_org_model.dart';
import '../bloc/child_clients_cubit.dart';

class ChildClientsView extends StatelessWidget {
  const ChildClientsView({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider<ChildClientsCubit>(
      create: (context) => ChildClientsCubit(
        repository: ClientsRepository(apiClient: context.read<ApiClient>()),
      ),
      child: const _ChildClientsContent(),
    );
  }
}

class _ChildClientsContent extends StatefulWidget {
  const _ChildClientsContent();

  @override
  State<_ChildClientsContent> createState() => _ChildClientsContentState();
}

class _ChildClientsContentState extends State<_ChildClientsContent> {
  List<ClientModel> _parents = const [];
  String _search = '';

  @override
  void initState() {
    super.initState();
    _loadParents();
  }

  Future<void> _loadParents() async {
    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final result = await repository.fetchClients(
        queryParams: {'all': true, AppStrings.FILTER_BY_STATUS: ClientStatusX.VERIFIED},
      );
      if (!mounted) return;
      setState(() => _parents = result.results);
      // Default to the first client so the table opens in sync, not empty.
      if (_parents.isNotEmpty) {
        final ChildClientsCubit cubit = context.read<ChildClientsCubit>();
        if (cubit.state.parent == null) cubit.selectParent(_parents.first);
      }
    } catch (_) {}
  }

  ClientModel? _parentById(String? id) {
    if (id == null || id.isEmpty) return null;
    for (final client in _parents) {
      if (client.publicId == id) return client;
    }
    return null;
  }

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    final ChildClientsCubit cubit = context.read<ChildClientsCubit>();
    final ClientModel? parent = _parentById(
      filters?[AppStrings.FILTER_BY_PARENT_CLIENT],
    );
    if (parent != null && cubit.state.parent?.publicId != parent.publicId) {
      cubit.selectParent(parent);
    }
    final String term = search ?? '';
    if (term != _search) setState(() => _search = term);
  }

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<ChildClientsCubit, ChildClientsState>(
      builder: (context, state) {
        final ChildClientsCubit cubit = context.read<ChildClientsCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(child: _Body(state: state, parents: _parents, search: _search, cubit: cubit, onFetchData: _onFetchData)),
            ],
          ),
        );
      },
    );
  }
}

class _Body extends StatelessWidget {
  final ChildClientsState state;
  final List<ClientModel> parents;
  final String search;
  final ChildClientsCubit cubit;
  final TableFetchCallback onFetchData;

  const _Body({
    required this.state,
    required this.parents,
    required this.search,
    required this.cubit,
    required this.onFetchData,
  });

  static const List<AppDataColumn> _columns = [
    AppDataColumn(
      id: 'party_name',
      label: AppStrings.COLUMN_CHILD_PARTY_NAME,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: 'village',
      label: AppStrings.COLUMN_CHILD_VILLAGE,
      width: AppSizes.tableColumnWidthCompact,
    ),
    AppDataColumn(
      id: 'address',
      label: AppStrings.COLUMN_CHILD_ADDRESS,
      width: AppSizes.tableColumnWidthWide,
    ),
    AppDataColumn(
      id: 'transport',
      label: AppStrings.COLUMN_CHILD_TRANSPORT,
      width: AppSizes.tableColumnWidthMedium,
    ),
    AppDataColumn(
      id: 'contact',
      label: AppStrings.COLUMN_CHILD_CONTACT,
      width: AppSizes.tableColumnWidthMedium,
    ),
  ];

  List<FilterValueOption> _parentOptions(String key) {
    if (key != AppStrings.FILTER_BY_PARENT_CLIENT) return const [];
    return parents
        .map(
          (client) => FilterValueOption(
            value: client.publicId,
            label: client.companyName,
          ),
        )
        .toList();
  }

  String _filterValueLabel(String key, String value) {
    if (key == AppStrings.FILTER_BY_PARENT_CLIENT) {
      for (final client in parents) {
        if (client.publicId == value) return client.companyName;
      }
    }
    return value;
  }

  List<ChildOrgModel> get _visibleChildren {
    final String term = search.trim().toLowerCase();
    if (term.isEmpty) return state.children;
    return state.children.where((child) {
      return child.partyName.toLowerCase().contains(term) ||
          child.villageName.toLowerCase().contains(term) ||
          (child.transportName).toLowerCase().contains(term) ||
          (child.contactNumber ?? '').toLowerCase().contains(term);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    if (state.parent == null) {
      return _Message(
        icon: Icons.storefront_outlined,
        title: AppStrings.CHILD_CLIENTS_EMPTY_NO_PARENT,
        body: AppStrings.CHILD_CLIENTS_EMPTY_NO_PARENT_BODY,
      );
    }

    if (state.status == ChildClientsStatus.failure) {
      return _Message(
        icon: Icons.error_outline_rounded,
        title: AppStrings.CHILD_CLIENTS_LOAD_FAILED,
        body: state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
        isError: true,
      );
    }

    return AppDataTable<ChildOrgModel>(
      items: _visibleChildren,
      isLoading: state.isLoading,
      currentPage: 1,
      totalPages: 1,
      totalItems: _visibleChildren.length,
      columns: _columns,
      configKey: 'child-clients',
      onFetchData: onFetchData,
      filterByOptions: const [AppStrings.FILTER_BY_PARENT_CLIENT],
      lockedFilters: const {AppStrings.FILTER_BY_PARENT_CLIENT},
      currentFilters: {
        AppStrings.FILTER_BY_PARENT_CLIENT: state.parent!.publicId,
      },
      filterValueOptions: _parentOptions,
      getFilterValueLabel: _filterValueLabel,
      getHumanReadableFilterName: (key) => AppStrings.CHILD_CLIENTS_PICK_PARENT,
      getFilterDescription: (key) => AppStrings.CHILD_CLIENTS_PICK_PARENT_HINT,
      searchBarActions: [
        IconActionButton(
          expand: true,
          icon: Icons.refresh_rounded,
          tooltip: AppStrings.TABLE_REFRESH,
          onPressed: state.isLoading ? null : cubit.refresh,
        ),
      ],
      searchHintText: AppStrings.CHILD_CLIENTS_PICK_PARENT_HINT,
      emptyTitle: AppStrings.CHILD_CLIENTS_EMPTY_TITLE,
      emptyDescription: AppStrings.CHILD_CLIENTS_EMPTY_BODY,
      emptyIcon: Icons.account_tree_outlined,
      cellBuilder: _buildCell,
    );
  }

  Widget _buildCell(
    BuildContext context,
    ChildOrgModel child,
    AppDataColumn col,
  ) {
    switch (col.id) {
      case 'party_name':
        return _textCell(child.partyName, isStrong: true);
      case 'village':
        return _textCell(child.villageName);
      case 'address':
        return _textCell(child.address?.formatted ?? '');
      case 'transport':
        return _textCell(child.transportName);
      case 'contact':
        return _textCell(child.contactNumber ?? '');
      default:
        return _textCell(AppStrings.TABLE_VALUE_UNAVAILABLE);
    }
  }

  Widget _textCell(String value, {bool isStrong = false}) {
    final String text = value.trim().isEmpty
        ? AppStrings.TABLE_VALUE_UNAVAILABLE
        : value;
    return Text(
      text,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: isStrong
          ? AppTypography.tableCellStrong
          : AppTypography.tableCell.copyWith(color: AppColors.TEXT_PRIMARY),
    );
  }
}

class _Message extends StatelessWidget {
  final IconData icon;
  final String title;
  final String body;
  final bool isError;

  const _Message({
    required this.icon,
    required this.title,
    required this.body,
    this.isError = false,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: AppSizes.iconXxl,
              color: isError ? AppColors.ERROR : AppColors.TEXT_DISABLED,
            ),
            const SizedBox(height: AppSpacing.md),
            Text(title, style: AppTypography.titleMedium),
            const SizedBox(height: AppSpacing.xs),
            Text(
              body,
              textAlign: TextAlign.center,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ],
        ),
      ),
    );
  }
}