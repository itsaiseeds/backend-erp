import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:printing/printing.dart';
import '../../../../core/constants/app_strings.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/network/api_exception.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../core/theme/app_typography.dart';
import '../../../../core/utils/toast_utils.dart';
import '../../../../core/widgets/buttons/primary_button.dart';
import '../../../../core/widgets/buttons/secondary_button.dart';
import '../../../orders/data/models/order_model.dart';
import '../../../orders/data/orders_repository.dart';
import '../../data/models/return_order_model.dart';
import '../../utils/return_order_slip_generator.dart';

/// Fetches the parent order, then renders the return order's slip on screen
/// so it can be checked before downloading -- the slip needs the order's own
/// line prices to compute a net sale per returned item, which the return
/// order payload alone does not carry.
class ReturnOrderSlipDialog extends StatefulWidget {
  final ReturnOrderModel returnOrder;
  final ApiClient apiClient;

  const ReturnOrderSlipDialog({
    super.key,
    required this.returnOrder,
    required this.apiClient,
  });

  static Future<void> show(
    BuildContext context, {
    required ReturnOrderModel returnOrder,
    required ApiClient apiClient,
  }) {
    return showDialog<void>(
      context: context,
      barrierColor: AppColors.OVERLAY,
      builder: (_) => ReturnOrderSlipDialog(
        returnOrder: returnOrder,
        apiClient: apiClient,
      ),
    );
  }

  @override
  State<ReturnOrderSlipDialog> createState() => _ReturnOrderSlipDialogState();
}

class _ReturnOrderSlipDialogState extends State<ReturnOrderSlipDialog> {
  final FocusNode _shortcutFocus = FocusNode();

  bool _isLoading = true;
  String? _error;
  OrderModel? _order;
  Future<Uint8List>? _pdf;
  bool _isDownloading = false;
  bool _isPrinting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _shortcutFocus.requestFocus();
    });
    _load();
  }

  @override
  void dispose() {
    _shortcutFocus.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final OrdersRepository repository = OrdersRepository(
        apiClient: widget.apiClient,
      );
      final OrderModel order = await repository.fetchOrder(
        widget.returnOrder.order.publicId,
      );
      if (!mounted) return;
      setState(() {
        _order = order;
        _isLoading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = AppStrings.RETURN_SLIP_LOAD_FAILED;
        _isLoading = false;
      });
    }
  }

  String get _fileName =>
      '${AppStrings.RETURN_SLIP_FILE_PREFIX}'
      '${widget.returnOrder.publicId}.pdf';

  // Built once and reused, so previewing then downloading does not lay the
  // document out twice.
  Future<Uint8List> _buildPdf() {
    final OrderModel? order = _order;
    if (order == null) {
      throw StateError('The order has not loaded yet.');
    }
    return _pdf ??= ReturnOrderSlipGenerator.generate(
      returnOrder: widget.returnOrder,
      order: order,
    );
  }

  Future<void> _download() async {
    setState(() => _isDownloading = true);

    try {
      final Uint8List bytes = await _buildPdf();
      if (!mounted) return;
      await Printing.sharePdf(bytes: bytes, filename: _fileName);
    } catch (_) {
      if (!mounted) return;
      ToastUtils.showError(context, AppStrings.RETURN_SLIP_DOWNLOAD_FAILED);
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  Future<void> _print() async {
    if (_isPrinting) return;
    setState(() => _isPrinting = true);

    try {
      final Uint8List bytes = await _buildPdf();
      if (!mounted) return;
      await Printing.layoutPdf(onLayout: (_) => bytes, name: _fileName);
    } catch (_) {
      if (!mounted) return;
      ToastUtils.showError(context, AppStrings.RETURN_SLIP_PRINT_FAILED);
    } finally {
      if (mounted) setState(() => _isPrinting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final Size viewport = MediaQuery.sizeOf(context);

    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.keyP, control: true): _print,
        const SingleActivator(LogicalKeyboardKey.keyP, meta: true): _print,
      },
      child: Focus(
        focusNode: _shortcutFocus,
        autofocus: true,
        child: _buildDialog(viewport),
      ),
    );
  }

  Widget _buildDialog(Size viewport) {
    return Dialog(
      backgroundColor: AppColors.BACKGROUND,
      insetPadding: const EdgeInsets.all(AppSpacing.xl),
      clipBehavior: Clip.antiAlias,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.dialog),
      ),
      child: SizedBox(
        width: viewport.width * 0.72,
        height: viewport.height * 0.9,
        child: Column(
          children: [
            _buildHeader(),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    final bool canAct = !_isLoading && _error == null;

    return Container(
      color: AppColors.PRIMARY,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.smd,
      ),
      child: Row(
        children: [
          const Icon(
            Icons.receipt_long_outlined,
            size: AppSizes.iconLg,
            color: AppColors.TEXT_ON_PRIMARY,
          ),
          const SizedBox(width: AppSpacing.smd),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  AppStrings.RETURN_SLIP_PREVIEW_TITLE,
                  style: AppTypography.headingSmall.copyWith(
                    color: AppColors.TEXT_ON_PRIMARY,
                  ),
                ),
                Text(
                  widget.returnOrder.publicId,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.SIDEBAR_ON_PRIMARY_MUTED,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          SecondaryButton(
            label: AppStrings.PRINT,
            icon: Icons.print_outlined,
            isLoading: _isPrinting,
            onPressed: canAct && !_isPrinting ? _print : null,
          ),
          const SizedBox(width: AppSpacing.sm),
          PrimaryButton(
            label: AppStrings.DOWNLOAD,
            icon: Icons.download_outlined,
            isLoading: _isDownloading,
            onPressed: canAct && !_isDownloading ? _download : null,
          ),
          const SizedBox(width: AppSpacing.sm),
          // Plain white: the shared IconActionButton paints itself in theme
          // green, which disappears against this header.
          IconButton(
            icon: const Icon(Icons.close_rounded),
            color: AppColors.TEXT_ON_PRIMARY,
            iconSize: AppSizes.iconLg,
            tooltip: AppStrings.CANCEL,
            splashRadius: AppSizes.iconLg,
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.PRIMARY),
      );
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline_rounded,
                size: AppSizes.iconXxl,
                color: AppColors.TEXT_DISABLED,
              ),
              const SizedBox(height: AppSpacing.smd),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: AppTypography.bodyMedium.copyWith(
                  color: AppColors.TEXT_SECONDARY,
                ),
              ),
              const SizedBox(height: AppSpacing.smd),
              PrimaryButton(label: AppStrings.RETRY, onPressed: _load),
            ],
          ),
        ),
      );
    }

    return PdfPreview(
      build: (format) => _buildPdf(),
      pdfFileName: _fileName,
      canChangeOrientation: false,
      canChangePageFormat: false,
      canDebug: false,
      allowPrinting: false,
      allowSharing: false,
      useActions: false,
      loadingWidget: const Center(
        child: CircularProgressIndicator(color: AppColors.PRIMARY),
      ),
    );
  }
}
