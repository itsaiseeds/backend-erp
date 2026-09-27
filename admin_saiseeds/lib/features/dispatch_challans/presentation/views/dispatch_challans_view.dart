import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:printing/printing.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/icon_action_button.dart';
import '../../data/dispatch_challans_repository.dart';
import '../../data/models/dispatch_challan_model.dart';
import '../../utils/challan_generator.dart';
import '../bloc/dispatch_challans_cubit.dart';
import '../widgets/challan_detail_dialog.dart';
import '../widgets/challan_preview_dialog.dart';
import '../widgets/dispatch_challans_table.dart';

class DispatchChallansView extends StatelessWidget {
  const DispatchChallansView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    return BlocProvider<DispatchChallansCubit>(
      create: (context) => DispatchChallansCubit(
        repository: DispatchChallansRepository(apiClient: apiClient),
      )..loadChallans(),
      child: const _DispatchChallansContent(),
    );
  }
}

class _DispatchChallansContent extends StatefulWidget {
  const _DispatchChallansContent();

  @override
  State<_DispatchChallansContent> createState() =>
      _DispatchChallansContentState();
}

class _DispatchChallansContentState extends State<_DispatchChallansContent> {
  final GlobalKey<DispatchChallansTableState> _tableKey =
      GlobalKey<DispatchChallansTableState>();

  void _onFetchData({
    required int page,
    required int limit,
    String? search,
    String? sortBy,
    String? sortOrder,
    Map<String, String>? filters,
  }) {
    context.read<DispatchChallansCubit>().applyQuery(
      page: page,
      limit: limit,
      search: search,
      sortBy: sortBy,
      sortOrder: sortOrder,
      filters: filters,
    );
  }

  void _onPreview(DispatchChallanModel challan) {
    ChallanPreviewDialog.show(context, challan);
  }

  Future<void> _onDownload(DispatchChallanModel challan) async {
    try {
      final Uint8List bytes = await ChallanGenerator.generate(challan);
      if (!mounted) return;

      await Printing.sharePdf(
        bytes: bytes,
        filename: '${AppStrings.CHALLAN_FILE_PREFIX}'
            '${challan.dispatchPublicId}.pdf',
      );
    } catch (_) {
      if (!mounted) return;
      ToastUtils.showError(context, AppStrings.CHALLAN_DOWNLOAD_FAILED);
    }
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<DispatchChallansCubit, DispatchChallansState>(
      listenWhen: (previous, current) =>
          current.status == DispatchChallansStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.CHALLANS_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final DispatchChallansCubit cubit = context
            .read<DispatchChallansCubit>();

        return Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: DispatchChallansTable(
            key: _tableKey,
            challans: state.challans,
            isLoading: state.status == DispatchChallansStatus.loading,
            currentPage: state.currentPage,
            totalPages: state.totalPages,
            totalItems: state.totalItems,
            currentSortBy: state.sortBy,
            currentSortOrder: state.sortOrder,
            currentFilters: state.filters,
            availableFilters: state.availableFilters,
            availableSorts: state.availableSorts,
            onFetchData: _onFetchData,
            onView: (challan) => ChallanDetailDialog.show(context, challan),
            onPreview: _onPreview,
            onDownload: _onDownload,
            isMutating: state.isMutating,
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
