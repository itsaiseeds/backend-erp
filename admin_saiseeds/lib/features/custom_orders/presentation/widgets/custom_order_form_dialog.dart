import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:intl/intl.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/services/packagings_service.dart';
import '../../../../core/services/products_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/formatters/currency_formatter.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../../core/widgets/dialogs/app_record_dialog.dart';
import '../../../../core/widgets/feedback/section_title.dart';
import '../../../../core/widgets/inputs/app_text_field.dart';
import '../../../../core/widgets/inputs/searchable_field.dart';
import '../../../../core/widgets/inputs/single_date_field.dart';
import '../../../../core/widgets/layout/app_hairline.dart';
import '../../../clients/data/clients_repository.dart';
import '../../../clients/data/models/client_address_model.dart';
import '../../../clients/data/models/client_model.dart';
import '../../../clients/data/models/client_status.dart';
import '../../../product_packagings/data/models/product_packaging_model.dart';
import '../../../product_packagings/data/product_packagings_repository.dart';
import '../../../orders/presentation/widgets/order_product_picker_dialog.dart';
import '../bloc/custom_orders_cubit.dart';
import 'custom_order_line_row.dart';

/// Books a custom order over the same three steps as a regular one.
class CustomOrderFormDialog extends StatefulWidget {
  const CustomOrderFormDialog({super.key});

  static final DateFormat isoDate = DateFormat('yyyy-MM-dd');

  static Future<void> show(
    BuildContext context, {
    required CustomOrdersCubit cubit,
  }) {
    return showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => BlocProvider<CustomOrdersCubit>.value(
        value: cubit,
        child: const CustomOrderFormDialog(),
      ),
    );
  }

  @override
  State<CustomOrderFormDialog> createState() => _CustomOrderFormDialogState();
}

class _CustomOrderFormDialogState extends State<CustomOrderFormDialog> {
  static const List<IconData> _ICONS = [
    Icons.storefront_outlined,
    Icons.inventory_2_outlined,
    Icons.local_shipping_outlined,
  ];

  static const List<String> _STEPS = [
    AppStrings.CUSTOM_ORDER_STEP_CLIENT,
    AppStrings.ORDER_STEP_ITEMS,
    AppStrings.ORDER_STEP_DELIVERY,
  ];

  static const List<String> _CAPTIONS = [
    AppStrings.CUSTOM_ORDER_STEP_CLIENT_CAPTION,
    AppStrings.CUSTOM_ORDER_STEP_ITEMS_CAPTION,
    AppStrings.CUSTOM_ORDER_STEP_DELIVERY_CAPTION,
  ];

  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final TextEditingController _commentsController = TextEditingController();

  List<CustomOrderLine> _lines = [];
  List<ClientModel> _clients = [];
  ClientModel? _client;
  List<ClientAddressModel> _addresses = const [];
  ClientAddressModel? _address;
  bool _isLoadingAddresses = false;
  DateTime? _expectedDelivery;

  int _stepIndex = 0;
  bool _isLoadingClients = true;
  bool _isSubmitting = false;
  String? _clientError;
  String? _addressError;
  String? _linesError;

  bool get _isFirstStep => _stepIndex == 0;

  bool get _isLastStep => _stepIndex == _STEPS.length - 1;

  bool get _canEdit => !_isSubmitting;

  @override
  void initState() {
    super.initState();
    _loadClients();
    _loadCatalogue();
  }

  /// Products and packagings feed the line pickers. They are fetched when the
  /// dialog opens rather than on tab entry, so simply listing orders costs
  /// nothing extra.
  Future<void> _loadCatalogue() async {
    await Future.wait([
      ProductsService.instance.loadProducts(),
      PackagingsService.instance.loadPackagings(),
    ]);
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _commentsController.dispose();
    for (final CustomOrderLine line in _lines) {
      line.dispose();
    }
    super.dispose();
  }

  /// Only verified clients can be ordered for, so the list is filtered rather
  /// than letting the API reject the choice after the fact.
  Future<void> _loadClients() async {
    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final result = await repository.fetchClients(
        queryParams: {
          'all': true,
          AppStrings.FILTER_BY_STATUS: ClientStatusX.VERIFIED,
        },
      );
      if (!mounted) return;
      setState(() {
        _clients = result.results;
        _isLoadingClients = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingClients = false);
    }
  }



  Future<void> _loadAddresses(ClientModel client) async {
    setState(() {
      _isLoadingAddresses = true;
      _addresses = const [];
      _address = null;
    });

    try {
      final ClientsRepository repository = ClientsRepository(
        apiClient: context.read<ApiClient>(),
      );
      final ClientModel full = await repository.fetchClient(client.publicId);
      if (!mounted || _client?.publicId != client.publicId) return;

      setState(() {
        _addresses = full.addresses;
        _address = _addresses.isEmpty ? null : _primaryOf(_addresses);
        _isLoadingAddresses = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingAddresses = false);
    }
  }

  static ClientAddressModel _primaryOf(List<ClientAddressModel> addresses) {
    for (final ClientAddressModel address in addresses) {
      if (address.isPrimary) return address;
    }
    return addresses.first;
  }

  bool _validateClient() {
    final bool clientValid = _client != null;
    final bool addressValid = _address != null;

    setState(() {
      _clientError = clientValid
          ? null
          : AppStrings.VALIDATION_CLIENT_REQUIRED;
      _addressError = addressValid
          ? null
          : AppStrings.VALIDATION_ADDRESS_REQUIRED;
    });

    return clientValid && addressValid;
  }

  bool _validateLines() {
    final bool formValid = _formKey.currentState?.validate() ?? false;
    final bool linesValid =
        _lines.isNotEmpty && _lines.every((line) => line.isValid);

    setState(
      () => _linesError = linesValid
          ? null
          : AppStrings.CUSTOM_ORDER_LINE_INVALID,
    );

    return formValid && linesValid;
  }

  void _goTo(int index) {
    // Each step gates the next, so a later step is never reached with the
    // earlier one incomplete.
    if (index > _stepIndex) {
      if (_stepIndex == 0 && !_validateClient()) return;
      if (_stepIndex == 1 && !_validateLines()) return;
    }
    setState(() => _stepIndex = index.clamp(0, _STEPS.length - 1));
  }

  /// Opens the product grid and appends what was chosen. A packaging already
  /// on the order merges into its line rather than posting a duplicate.
  Future<void> _addLine() async {
    final List<PickedPackaging>? picked = await OrderProductPickerDialog.show(
      context,
      repository: ProductPackagingsRepository(
        apiClient: context.read<ApiClient>(),
      ),
      existingPublicIds: {for (final CustomOrderLine line in _lines) line.key},
    );
    if (picked == null || picked.isEmpty || !mounted) return;

    setState(() {
      for (final PickedPackaging entry in picked) {
        final ProductPackagingModel source = entry.packaging;
        final String key = '${source.productPublicId}|${source.packetWeight}';

        final int existing = _lines.indexWhere((line) => line.key == key);
        if (existing != -1) {
          _lines[existing].packets += entry.quantity;
          continue;
        }

        _lines = [
          ..._lines,
          CustomOrderLine(
            product: ProductsService.instance.productByPublicId(
              source.productPublicId,
            ),
            productPublicId: source.productPublicId,
            productName: source.productName,
            imageUrl:
                ProductsService.instance
                    .productByPublicId(source.productPublicId)
                    ?.imageUrl ??
                '',
            packetWeight: source.packetWeight,
            packetsPerBag: source.packets,
            packets: entry.quantity,
            priceText: source.sellingPrice,
          ),
        ];
      }
    });
  }

  void _removeLine(int index) {
    setState(() {
      final List<CustomOrderLine> next = [..._lines];
      next.removeAt(index).dispose();
      _lines = next;
    });
  }

  void _changePackets(int index, int delta) {
    final int next = _lines[index].packets + delta;
    if (next < 1) return;
    setState(() => _lines[index].packets = next);
  }

  num get _liveTotalAmount =>
      _lines.fold<num>(0, (sum, line) => sum + line.lineTotal);

  Future<void> _submit() async {
    if (!_validateClient()) {
      setState(() => _stepIndex = 0);
      return;
    }
    if (!_validateLines()) {
      setState(() => _stepIndex = 1);
      return;
    }

    setState(() => _isSubmitting = true);
    final CustomOrdersCubit cubit = context.read<CustomOrdersCubit>();

    final bool succeeded = await cubit.createCustomOrder({
      'client_public_id': _client!.publicId,
      'client_address_id': _address!.id,
      'special_comments': _commentsController.text.trim(),
      if (_expectedDelivery != null)
        'expected_delivery_date': CustomOrderFormDialog.isoDate.format(
          _expectedDelivery!,
        ),
      'items': [for (final CustomOrderLine line in _lines) line.toJson()],
    });

    if (!mounted) return;
    setState(() => _isSubmitting = false);

    if (succeeded) {
      Navigator.of(context).pop();
      ToastUtils.showSuccess(context, AppStrings.CUSTOM_ORDER_CREATED);
      return;
    }

    ToastUtils.showError(
      context,
      cubit.state.errorMessage ?? AppStrings.SOMETHING_WENT_WRONG,
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppRecordDialog(
      icon: Icons.tune_outlined,
      title: AppStrings.CUSTOM_ORDER_ADD,
      subtitle:
          '${AppStrings.ORDER_STEP_PREFIX} ${_stepIndex + 1}'
          '${AppStrings.LABEL_SEPARATOR} ${_CAPTIONS[_stepIndex]}',
      mode: RecordDialogMode.edit,
      isSubmitting: _isSubmitting,
      extraHeight: AppSizes.recordDialogRoomyBump * 2,
      onCancelEdit: _isFirstStep
          ? () => Navigator.of(context).pop()
          : () => _goTo(_stepIndex - 1),
      cancelLabel: _isFirstStep ? AppStrings.CANCEL : AppStrings.STEP_BACK,
      onSubmit: _isSubmitting
          ? null
          : (_isLastStep ? _submit : () => _goTo(_stepIndex + 1)),
      submitLabel: _isLastStep ? AppStrings.CREATE : AppStrings.STEP_NEXT,
      body: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            SectionTitle(
              title: _STEPS[_stepIndex],
              icon: _ICONS[_stepIndex],
              hasRule: true,
            ),
            const SizedBox(height: AppSpacing.md),
            _buildStep(),
          ],
        ),
      ),
    );
  }

  Widget _buildStep() {
    switch (_stepIndex) {
      case 1:
        return _buildItems();
      case 2:
        return _buildDelivery();
      default:
        return _buildClient();
    }
  }

  Widget _buildClient() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SearchableField<ClientModel>(
          label: AppStrings.COLUMN_ORDER_CLIENT,
          hintText: _isLoadingClients
              ? AppStrings.LOADING
              : AppStrings.FIELD_CLIENT_HINT,
          value: _client,
          items: _clients,
          itemToString: (client) => client.companyName,
          isSame: (a, b) => a.publicId == b.publicId,
          enabled: _canEdit && !_isLoadingClients,
          errorText: _clientError,
          onSelected: (client) {
            setState(() {
              _client = client;
              _clientError = null;
              _addressError = null;
            });
            _loadAddresses(client);
          },
        ),
        const SizedBox(height: AppSpacing.md),
        SearchableField<ClientAddressModel>(
          label: AppStrings.FIELD_DELIVERY_ADDRESS_PICK,
          hintText: _isLoadingAddresses
              ? AppStrings.LOADING
              : AppStrings.FIELD_DELIVERY_ADDRESS_PICK,
          value: _address,
          items: _addresses,
          itemToString: (address) => address.labelled,
          isSame: (a, b) => a.id == b.id,
          enabled: _canEdit && !_isLoadingAddresses && _addresses.isNotEmpty,
          errorText: _addressError,
          onSelected: (address) => setState(() {
            _address = address;
            _addressError = null;
          }),
        ),
      ],
    );
  }

  Widget _buildItems() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (_lines.isEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: AppSpacing.sm),
            child: Text(
              AppStrings.CUSTOM_ORDER_NO_LINES,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.TEXT_SECONDARY,
              ),
            ),
          ),
        for (int index = 0; index < _lines.length; index++) ...[
          if (index > 0) ...[
            const SizedBox(height: AppSpacing.sm),
            const AppHairline(),
            const SizedBox(height: AppSpacing.sm),
          ],
          _buildLine(index),
        ],
        const SizedBox(height: AppSpacing.md),
        SecondaryButton(
          label: AppStrings.ORDER_ADD_ITEM,
          icon: Icons.add_rounded,
          onPressed: _canEdit ? _addLine : null,
        ),
        if (_linesError != null) ...[
          const SizedBox(height: AppSpacing.sm),
          Text(
            _linesError!,
            style: AppTypography.bodySmall.copyWith(color: AppColors.ERROR),
          ),
        ],
        const SizedBox(height: AppSpacing.md),
        Row(
          children: [
            Expanded(
              child: Text(
                AppStrings.COLUMN_ORDER_AMOUNT,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
            ),
            Text(
              CurrencyFormatter.rupees(_liveTotalAmount),
              style: AppTypography.labelStrong,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildLine(int index) {
    final CustomOrderLine line = _lines[index];

    return CustomOrderLineRow(
      line: line,
      isEditable: true,
      onIncrement: _canEdit ? () => _changePackets(index, 1) : null,
      onDecrement: !_canEdit || line.packets <= 1
          ? null
          : () => _changePackets(index, -1),
      onRemove: _canEdit ? () => _removeLine(index) : null,
      onPriceChanged: (_) => setState(() {}),
    );
  }

  Widget _buildDelivery() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        SingleDateField(
          label: AppStrings.FIELD_EXPECTED_DELIVERY,
          value: _expectedDelivery,
          enabled: _canEdit,
          onChanged: (date) => setState(() => _expectedDelivery = date),
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextField(
          controller: _commentsController,
          label: AppStrings.FIELD_SPECIAL_COMMENTS,
          hint: AppStrings.FIELD_SPECIAL_COMMENTS_HINT,
          enabled: _canEdit,
        ),
      ],
    );
  }
}
