import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../products/data/products_repository.dart';
import '../../data/stock_ledger_repository.dart';
import '../bloc/stock_ledger_cubit.dart';
import '../bloc/stock_ledger_state.dart';
import '../widgets/stock_ledger_chain.dart';
import '../widgets/stock_ledger_header.dart';
import '../widgets/stock_ledger_inspector.dart';
import '../widgets/stock_ledger_minimap.dart';

/// The investigative "git log for stock" screen: pick a product and a date
/// window, then walk every stock event that touched it, in order, with the
/// full before/after state of every pool at each step.
class StockLedgerView extends StatelessWidget {
  const StockLedgerView({super.key});

  @override
  Widget build(BuildContext context) {
    final ApiClient apiClient = context.read<ApiClient>();

    ProductsService.instance.repository = ProductsRepository(
      apiClient: apiClient,
    );

    return BlocProvider<StockLedgerCubit>(
      create: (context) => StockLedgerCubit(
        repository: StockLedgerRepository(apiClient: apiClient),
      ),
      child: const _StockLedgerContent(),
    );
  }
}

class _StockLedgerContent extends StatefulWidget {
  const _StockLedgerContent();

  @override
  State<_StockLedgerContent> createState() => _StockLedgerContentState();
}

class _StockLedgerContentState extends State<_StockLedgerContent> {
  @override
  void initState() {
    super.initState();
    _loadProducts();
    final DateTime today = DateTime.now();
    final DateTime todayOnly = DateTime(today.year, today.month, today.day);
    context.read<StockLedgerCubit>().setDateRange(todayOnly, todayOnly);
  }

  Future<void> _loadProducts() async {
    await ProductsService.instance.loadProducts();
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<StockLedgerCubit, StockLedgerState>(
      listenWhen: (previous, current) =>
          current.status == StockLedgerStatus.failure &&
          previous.errorMessage != current.errorMessage,
      listener: (context, state) {
        ToastUtils.showError(
          context,
          AppStrings.STOCK_LEDGER_LOAD_FAILED_TITLE,
          description: state.errorMessage,
        );
      },
      builder: (context, state) {
        final bool narrow = MediaQuery.sizeOf(context).width < 1100;

        return Container(
          color: AppColors.BACKGROUND,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const StockLedgerHeader(),
              Expanded(
                child: Stack(
                  children: [
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(
                          width: 220,
                          child: StockLedgerMinimap(),
                        ),
                        const VerticalDivider(
                          width: 1,
                          color: AppColors.BORDER,
                        ),
                        const Expanded(child: StockLedgerChain()),
                        if (!narrow) ...[
                          const VerticalDivider(
                            width: 1,
                            color: AppColors.BORDER,
                          ),
                          const SizedBox(
                            width: 340,
                            child: StockLedgerInspector(narrow: false),
                          ),
                        ],
                      ],
                    ),
                    if (narrow && state.selectedRow != null) ...[
                      if (state.inspectorOpenOnNarrow)
                        Positioned.fill(
                          child: GestureDetector(
                            onTap: () => context
                                .read<StockLedgerCubit>()
                                .setInspectorOpenOnNarrow(false),
                            child: Container(color: AppColors.OVERLAY),
                          ),
                        ),
                      if (state.inspectorOpenOnNarrow)
                        Positioned(
                          top: 0,
                          right: 0,
                          bottom: 0,
                          width: 360,
                          child: Material(
                            elevation: 12,
                            child: const StockLedgerInspector(narrow: true),
                          ),
                        )
                      else
                        Positioned(
                          right: 16,
                          bottom: 16,
                          child: _InspectorFab(
                            onTap: () => context
                                .read<StockLedgerCubit>()
                                .setInspectorOpenOnNarrow(true),
                          ),
                        ),
                    ],
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

class _InspectorFab extends StatelessWidget {
  final VoidCallback onTap;

  const _InspectorFab({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.PRIMARY,
      borderRadius: BorderRadius.circular(999),
      elevation: 4,
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: const Padding(
          padding: EdgeInsets.symmetric(horizontal: 14, vertical: 9),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.vertical_split_rounded,
                size: 18,
                color: AppColors.TEXT_ON_PRIMARY,
              ),
              SizedBox(width: 6),
              Text(
                AppStrings.STOCK_LEDGER_INSPECTOR_OPEN,
                style: TextStyle(
                  color: AppColors.TEXT_ON_PRIMARY,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
