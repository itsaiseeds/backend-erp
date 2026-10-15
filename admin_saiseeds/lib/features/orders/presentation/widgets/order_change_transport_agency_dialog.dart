import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/dialogs/app_form_dialog.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/transport_agency_model.dart';
import '../../data/models/order_model.dart';
import '../bloc/orders_cubit.dart';

/// Reassigns a dispatched, agency order to a different transport agency, one
/// of the order's own client's own agencies.
///
/// [TransportAgencyModel.id] here is a `ClientTransportAgency` link id, not
/// the `TransportAgency`'s own id -- `OrdersRepository.changeTransportAgency`
/// sends that link id, mirroring `edit-order`'s `client_transport_agency_id`
/// field, the one other write in this app that picks a client's agency.
class OrderChangeTransportAgencyDialog extends StatefulWidget {
  final OrderModel order;

  const OrderChangeTransportAgencyDialog({super.key, required this.order});

  static Future<void> show(
    BuildContext context,
    OrderModel order, {
    required OrdersCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<OrdersCubit>.value(
        value: cubit,
        child: OrderChangeTransportAgencyDialog(order: order),
      ),
    );
  }

  @override
  State<OrderChangeTransportAgencyDialog> createState() =>
      _OrderChangeTransportAgencyDialogState();
}

class _OrderChangeTransportAgencyDialogState
    extends State<OrderChangeTransportAgencyDialog> {
  List<TransportAgencyModel> _agencies = const [];
  TransportAgencyModel? _selected;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _selectionError;

  @override
  void initState() {
    super.initState();
    _loadAgencies();
  }

  Future<void> _loadAgencies() async {
    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final full = await repository.fetchClient(widget.order.client.publicId);
      if (!mounted) return;
      setState(() {
        _agencies = full.transportAgencies;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _submit() async {
    if (_selected == null) {
      setState(
        () => _selectionError = AppStrings.VALIDATION_TRANSPORT_AGENCY_REQUIRED,
      );
      return;
    }

    setState(() => _isSubmitting = true);
    final OrdersCubit cubit = context.read<OrdersCubit>();

    final bool succeeded = await cubit.changeTransportAgency(
      publicId: widget.order.publicId,
      transportAgencyId: _selected!.id,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(
        context,
        AppStrings.ORDER_CHANGE_TRANSPORT_AGENCY_DONE,
      );
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppFormDialog(
      icon: Icons.sync_alt_outlined,
      title: AppStrings.ORDER_CHANGE_TRANSPORT_AGENCY,
      subtitle: AppStrings.ORDER_CHANGE_TRANSPORT_AGENCY_SUBTITLE,
      width: AppSizes.formDialogCompactWidth,
      submitLabel: AppStrings.SAVE,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting || _isLoading ? null : _submit,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (widget.order.agencyName.isNotEmpty) ...[
            Text(
              '${AppStrings.ORDER_CHANGE_TRANSPORT_AGENCY_CURRENT} '
              '${widget.order.agencyName}',
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else
            SearchableField<TransportAgencyModel>(
              label: AppStrings.FIELD_TRANSPORT_AGENCY,
              hintText: AppStrings.FIELD_TRANSPORT_AGENCY_HINT,
              value: _selected,
              items: _agencies,
              itemToString: (agency) => agency.name,
              isSame: (a, b) => a.id == b.id,
              enabled: !_isSubmitting && _agencies.isNotEmpty,
              errorText: _selectionError,
              emptyHint: AppStrings.ORDER_CHANGE_TRANSPORT_AGENCY_NONE,
              onSelected: (agency) => setState(() {
                _selected = agency;
                _selectionError = null;
              }),
            ),
        ],
      ),
    );
  }
}
