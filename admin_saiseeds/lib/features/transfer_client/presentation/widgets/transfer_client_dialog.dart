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
import '../../../sales_people/data/models/sales_person_model.dart';
import '../../../sales_people/data/sales_people_repository.dart';
import '../bloc/transfer_client_cubit.dart';

/// Picks a new, active sales person to receive the already-selected clients,
/// then calls [TransferClientCubit.transferClients].
class TransferClientDialog extends StatefulWidget {
  final List<String> clientIds;
  final List<String> clientLabels;

  const TransferClientDialog({
    super.key,
    required this.clientIds,
    required this.clientLabels,
  });

  static Future<bool?> show(
    BuildContext context, {
    required TransferClientCubit cubit,
    required List<String> clientIds,
    required List<String> clientLabels,
  }) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<TransferClientCubit>.value(
        value: cubit,
        child: TransferClientDialog(
          clientIds: clientIds,
          clientLabels: clientLabels,
        ),
      ),
    );
  }

  @override
  State<TransferClientDialog> createState() => _TransferClientDialogState();
}

class _TransferClientDialogState extends State<TransferClientDialog> {
  List<SalesPersonModel> _targets = const [];
  SalesPersonModel? _selected;
  bool _isLoading = true;
  bool _isSubmitting = false;
  String? _selectionError;

  @override
  void initState() {
    super.initState();
    _loadTargets();
  }

  Future<void> _loadTargets() async {
    try {
      final SalesPeopleRepository repository = SalesPeopleRepository(
        apiClient: context.read<ApiClient>(),
      );
      final List<SalesPersonModel> people = await repository
          .fetchSalesPeople();
      if (!mounted) return;
      setState(() {
        _targets = people;
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
        () => _selectionError =
            AppStrings.VALIDATION_TARGET_SALES_PERSON_REQUIRED,
      );
      return;
    }

    final int? targetId = int.tryParse(_selected!.id);
    if (targetId == null) {
      setState(
        () => _selectionError = AppStrings.SOMETHING_WENT_WRONG,
      );
      return;
    }

    setState(() => _isSubmitting = true);
    final TransferClientCubit cubit = context.read<TransferClientCubit>();

    final bool succeeded = await cubit.transferClients(
      clientIds: widget.clientIds,
      targetSalesPersonId: targetId,
    );

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop(true);
      ToastUtils.showSuccess(context, AppStrings.TRANSFER_CLIENT_DONE);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.transferErrorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    final int count = widget.clientIds.length;
    final String countLabel = count == 1
        ? AppStrings.TRANSFER_CLIENT_DIALOG_SELECTED_COUNT_SINGULAR
        : AppStrings.TRANSFER_CLIENT_DIALOG_SELECTED_COUNT_PLURAL;

    return AppFormDialog(
      icon: Icons.swap_horizontal_circle_outlined,
      title: AppStrings.TRANSFER_CLIENT_DIALOG_TITLE,
      subtitle: AppStrings.TRANSFER_CLIENT_DIALOG_SUBTITLE,
      width: AppSizes.formDialogCompactWidth,
      submitLabel: AppStrings.TRANSFER_CLIENT_ACTION,
      isSubmitting: _isSubmitting,
      onSubmit: _isSubmitting || _isLoading ? null : _submit,
      content: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$count $countLabel',
            style: AppTypography.labelStrong,
          ),
          const SizedBox(height: AppSpacing.xs),
          Text(
            widget.clientLabels.join(', '),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.TEXT_SECONDARY,
            ),
          ),
          const SizedBox(height: AppSpacing.md),
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: AppSpacing.md),
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            )
          else
            SearchableField<SalesPersonModel>(
              label: AppStrings.TRANSFER_CLIENT_TARGET_FIELD,
              hintText: AppStrings.TRANSFER_CLIENT_TARGET_HINT,
              value: _selected,
              items: _targets,
              itemToString: (person) => person.name,
              isSame: (a, b) => a.id == b.id,
              enabled: !_isSubmitting && _targets.isNotEmpty,
              errorText: _selectionError,
              emptyHint: AppStrings.TRANSFER_CLIENT_TARGET_NONE,
              onSelected: (person) => setState(() {
                _selected = person;
                _selectionError = null;
              }),
            ),
        ],
      ),
    );
  }
}
