import 'package:flutter/services.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import '../../../core/utils/formatters/date_formatter.dart';
import '../../orders/data/models/order_model.dart';
import '../data/models/return_order_model.dart';
import '../data/models/return_order_status.dart';

/// One returned line paired with the order line it came from, so the PDF only
/// has to render precomputed values rather than do any matching itself.
///
/// The return records packets and a per-packet price; the order records bags
/// and a per-bag price. [originalLineTotal] converts the order's bag price to
/// a per-packet basis first (bag price / packets per bag), then multiplies by
/// the packets that bag line actually held, so both sides of the subtraction
/// are in the same unit. A `null` [originalLineTotal] means no order line
/// matched this product + packet weight -- shown as unavailable, never as a
/// silent zero.
class ReturnSlipLine {
  final ReturnOrderItemModel item;
  final OrderPackagingModel? matchedPackaging;
  final num? originalLineTotal;

  const ReturnSlipLine({
    required this.item,
    this.matchedPackaging,
    this.originalLineTotal,
  });

  num? get netSale =>
      originalLineTotal == null ? null : originalLineTotal! - item.lineTotal;
}

/// Matches a return order's items against the parent order's packagings and
/// computes the net sale per line.
class ReturnOrderSlipLines {
  ReturnOrderSlipLines._();

  /// Packet weights travel as floating point and a trailing ".0" or rounding
  /// noise would otherwise make an identical weight fail to match, so both
  /// sides are compared at 3-decimal precision -- plenty for a kg figure that
  /// is never entered more precisely than that.
  static String _weightKey(num weight) => weight.toStringAsFixed(3);

  static List<ReturnSlipLine> build(ReturnOrderModel returnOrder, OrderModel order) {
    return returnOrder.items.map((item) {
      final OrderPackagingModel? packaging = _match(item, order);
      if (packaging == null) {
        return ReturnSlipLine(item: item);
      }

      final num perPacketPrice = packaging.packets > 0
          ? packaging.negotiatedSellingPrice / packaging.packets
          : packaging.negotiatedSellingPrice;
      final int totalPacketsOnLine = packaging.packets * packaging.quantity;
      final num originalLineTotal = perPacketPrice * totalPacketsOnLine;

      return ReturnSlipLine(
        item: item,
        matchedPackaging: packaging,
        originalLineTotal: originalLineTotal,
      );
    }).toList(growable: false);
  }

  static OrderPackagingModel? _match(
    ReturnOrderItemModel item,
    OrderModel order,
  ) {
    final String productId = item.product.publicId;
    final String weightKey = _weightKey(item.packetWeight);

    for (final OrderPackagingModel packaging in order.packagings) {
      if (packaging.productPublicId != productId) continue;
      if (_weightKey(packaging.packetWeight) != weightKey) continue;
      return packaging;
    }
    return null;
  }
}

/// Renders an accepted return order to a printable A4 sheet.
///
/// Same house style as [ChallanGenerator] (dispatch_challans) -- this app's
/// documents read as one family -- but with nothing dispatch-specific: a
/// return slip says who the goods came back from and what came back, not how
/// they were carried.
class ReturnOrderSlipGenerator {
  ReturnOrderSlipGenerator._();

  static const PdfColor _primary = PdfColor.fromInt(0xFF1E7A34);
  static const PdfColor _primaryDark = PdfColor.fromInt(0xFF145523);
  static const PdfColor _tintStrong = PdfColor.fromInt(0xFFE8F3EA);
  static const PdfColor _tintSoft = PdfColor.fromInt(0xFFF4F9F5);
  static const PdfColor _textPrimary = PdfColor.fromInt(0xFF111111);
  static const PdfColor _textSecondary = PdfColor.fromInt(0xFF555555);
  static const PdfColor _textMuted = PdfColor.fromInt(0xFF999999);
  static const PdfColor _divider = PdfColor.fromInt(0xFFDCE0DC);
  static const PdfColor _white = PdfColor.fromInt(0xFFFFFFFF);

  static const double _hairline = 0.5;
  static const String _blank = '-';

  static Future<Uint8List> generate({
    required ReturnOrderModel returnOrder,
    required OrderModel order,
  }) async {
    final pw.Font base = await PdfGoogleFonts.interRegular();
    final pw.Font bold = await PdfGoogleFonts.interBold();
    final pw.Font italic = await PdfGoogleFonts.interItalic();

    final pw.Document doc = pw.Document(
      theme: pw.ThemeData.withFont(base: base, bold: bold, italic: italic),
    );

    final pw.MemoryImage? logo = await _loadLogo();
    final List<ReturnSlipLine> lines = ReturnOrderSlipLines.build(
      returnOrder,
      order,
    );

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        header: (context) => context.pageNumber == 1
            ? pw.SizedBox()
            : pw.Padding(
                padding: const pw.EdgeInsets.only(bottom: 10),
                child: _continuationHeader(returnOrder),
              ),
        footer: (context) => pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.stretch,
          mainAxisSize: pw.MainAxisSize.min,
          children: [_footer(context)],
        ),
        build: (context) => [
          _header(returnOrder, logo),
          pw.SizedBox(height: 12),
          _partyCard(returnOrder, order),
          pw.SizedBox(height: 10),
          _summaryStrip(returnOrder),
          pw.SizedBox(height: 12),
          _itemsTable(lines),
          pw.SizedBox(height: 4),
          _netSaleNote(),
          pw.SizedBox(height: 10),
          _totalsRow(lines, returnOrder),
        ],
      ),
    );

    return doc.save();
  }

  static Future<pw.MemoryImage?> _loadLogo() async {
    try {
      final ByteData data = await rootBundle.load(
        'assets/logo/saiseeds-logo.png',
      );
      return pw.MemoryImage(data.buffer.asUint8List());
    } catch (_) {
      return null;
    }
  }

  // ══════════════ HEADER ══════════════

  static pw.Widget _header(ReturnOrderModel returnOrder, pw.MemoryImage? logo) {
    // Same seller block the dispatch challan prints -- one company, one
    // source of truth for its letterhead, so both documents introduce
    // themselves the same way.
    const String companyAddress =
        '55, Gangotri Complex, Visnagar Road, Mansa, Gandhinagar (382845)';
    const String gstNumber = '24ACGFS1809R1ZO';
    const String stateName = 'Gujarat';
    const String contactNumber = '9624532999';
    const String email = 'info@saiseeds.in';
    const String web = 'saiseeds.in';

    const String taxLine = 'GSTIN: $gstNumber   |   State: $stateName';
    const String reachLine = 'Ph: $contactNumber   |   $email   |   $web';

    return pw.Column(
      children: [
        pw.Row(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            if (logo != null) ...[
              pw.Image(logo, width: 52, height: 52),
              pw.SizedBox(width: 10),
            ],
            pw.Expanded(
              child: pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Text(
                    'Saiseeds Company',
                    style: pw.TextStyle(
                      fontSize: 18,
                      fontWeight: pw.FontWeight.bold,
                      color: _primary,
                    ),
                  ),
                  pw.SizedBox(height: 2),
                  pw.Text(
                    companyAddress,
                    style: const pw.TextStyle(
                      fontSize: 7.5,
                      color: _textSecondary,
                      lineSpacing: 1.2,
                    ),
                  ),
                  pw.SizedBox(height: 2),
                  pw.Text(
                    taxLine,
                    style: const pw.TextStyle(fontSize: 7, color: _textMuted),
                  ),
                  pw.SizedBox(height: 1),
                  pw.Text(
                    reachLine,
                    style: const pw.TextStyle(fontSize: 7, color: _primary),
                  ),
                ],
              ),
            ),
            pw.SizedBox(width: 10),
            pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.end,
              children: [
                pw.Text(
                  'RETURN ORDER SLIP',
                  style: pw.TextStyle(
                    fontSize: 14,
                    fontWeight: pw.FontWeight.bold,
                    color: _primaryDark,
                    letterSpacing: 1.4,
                  ),
                ),
                pw.SizedBox(height: 5),
                _kv('Return No:', returnOrder.publicId),
                _kv('Order No:', returnOrder.order.publicId),
                _kv('Return Date:', _date(returnOrder.returnDate)),
                _kv('Status:', _statusLabel(returnOrder)),
              ],
            ),
          ],
        ),
        pw.SizedBox(height: 8),
        pw.Container(height: 2, color: _primary),
      ],
    );
  }

  static pw.Widget _continuationHeader(ReturnOrderModel returnOrder) {
    return pw.Column(
      children: [
        pw.Row(
          mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
          children: [
            pw.Text(
              'RETURN ORDER SLIP  ${returnOrder.publicId}',
              style: pw.TextStyle(
                fontSize: 8,
                fontWeight: pw.FontWeight.bold,
                color: _primaryDark,
              ),
            ),
            pw.Text(
              returnOrder.client.companyName,
              style: const pw.TextStyle(fontSize: 7.5, color: _textSecondary),
            ),
          ],
        ),
        pw.SizedBox(height: 4),
        pw.Container(height: 1, color: _primary),
      ],
    );
  }

  static pw.Widget _kv(String label, String value) {
    return pw.Padding(
      padding: const pw.EdgeInsets.only(bottom: 2),
      child: pw.Row(
        mainAxisSize: pw.MainAxisSize.min,
        children: [
          pw.Text(
            label,
            style: pw.TextStyle(
              fontSize: 7.5,
              fontWeight: pw.FontWeight.bold,
              color: _textSecondary,
            ),
          ),
          pw.SizedBox(width: 4),
          pw.Text(
            value.isEmpty ? _blank : value,
            style: pw.TextStyle(
              fontSize: 7.5,
              color: _textPrimary,
              fontWeight: pw.FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  static String _statusLabel(ReturnOrderModel returnOrder) {
    switch (returnOrder.status) {
      case ReturnOrderStatus.accepted:
        return 'Accepted';
      case ReturnOrderStatus.pending:
        return 'Pending';
      case ReturnOrderStatus.rejected:
        return 'Rejected';
      case ReturnOrderStatus.unknown:
        return _blank;
    }
  }

  // ══════════════ PARTY ══════════════

  static pw.Widget _partyCard(ReturnOrderModel returnOrder, OrderModel order) {
    final String address = order.deliveryToLabel.isNotEmpty
        ? order.deliveryToLabel
        : order.deliveryAddress;

    return pw.Container(
      decoration: pw.BoxDecoration(
        border: pw.Border.all(color: _divider, width: _hairline),
        borderRadius: pw.BorderRadius.circular(3),
      ),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Container(
            width: double.infinity,
            color: _tintStrong,
            padding: const pw.EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: pw.Text(
              'RETURNED BY',
              style: pw.TextStyle(
                fontSize: 7,
                fontWeight: pw.FontWeight.bold,
                color: _primaryDark,
                letterSpacing: 0.8,
              ),
            ),
          ),
          pw.Padding(
            padding: const pw.EdgeInsets.fromLTRB(8, 6, 8, 7),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.start,
              children: [
                pw.Text(
                  returnOrder.client.companyName.isEmpty
                      ? _blank
                      : returnOrder.client.companyName,
                  style: pw.TextStyle(
                    fontSize: 9,
                    fontWeight: pw.FontWeight.bold,
                    color: _textPrimary,
                  ),
                ),
                if (address.isNotEmpty) ...[
                  pw.SizedBox(height: 2),
                  pw.Text(
                    address,
                    style: const pw.TextStyle(
                      fontSize: 7.5,
                      color: _textSecondary,
                      lineSpacing: 1.3,
                    ),
                  ),
                ],
                if (order.cityName.isNotEmpty) ...[
                  pw.SizedBox(height: 3),
                  _inlinePair('City', order.cityName),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  static pw.Widget _inlinePair(
    String label,
    String value, {
    double labelWidth = 52,
  }) {
    return pw.Row(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.SizedBox(
          width: labelWidth,
          child: pw.Text(
            label,
            style: pw.TextStyle(
              fontSize: 7,
              fontWeight: pw.FontWeight.bold,
              color: _textSecondary,
            ),
          ),
        ),
        pw.Expanded(
          child: pw.Text(
            value.isEmpty ? _blank : value,
            style: const pw.TextStyle(fontSize: 7.5, color: _textPrimary),
          ),
        ),
      ],
    );
  }

  // ══════════════ SUMMARY ══════════════

  static pw.Widget _summaryStrip(ReturnOrderModel returnOrder) {
    return pw.Container(
      decoration: pw.BoxDecoration(
        color: _tintSoft,
        border: pw.Border.all(color: _divider, width: _hairline),
        borderRadius: pw.BorderRadius.circular(3),
      ),
      padding: const pw.EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: pw.Row(
        children: [
          _summaryCell('RETURN DATE', _date(returnOrder.returnDate)),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell('TOTAL PACKETS', '${returnOrder.totalPackets}'),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell('TOTAL KG', '${_trim(returnOrder.totalKg)} kg'),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell(
            'TOTAL RETURNED AMOUNT',
            _amount(returnOrder.totalAmount),
          ),
        ],
      ),
    );
  }

  static pw.Widget _summaryCell(String label, String value) {
    return pw.Expanded(
      child: pw.Padding(
        padding: const pw.EdgeInsets.symmetric(horizontal: 8),
        child: pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.start,
          children: [
            pw.Text(
              label,
              style: pw.TextStyle(
                fontSize: 6,
                fontWeight: pw.FontWeight.bold,
                color: _textMuted,
                letterSpacing: 0.6,
              ),
            ),
            pw.SizedBox(height: 1),
            pw.Text(
              value.isEmpty ? _blank : value,
              style: pw.TextStyle(
                fontSize: 8,
                fontWeight: pw.FontWeight.bold,
                color: _textPrimary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ══════════════ ITEMS ══════════════

  static pw.Widget _itemsTable(List<ReturnSlipLine> lines) {
    return pw.Table(
      border: pw.TableBorder.all(color: _divider, width: _hairline),
      columnWidths: const {
        0: pw.FixedColumnWidth(20),
        1: pw.FlexColumnWidth(1.3),
        2: pw.FixedColumnWidth(42),
        3: pw.FixedColumnWidth(40),
        4: pw.FixedColumnWidth(48),
        5: pw.FixedColumnWidth(58),
        6: pw.FixedColumnWidth(58),
        7: pw.FixedColumnWidth(58),
      },
      children: [
        pw.TableRow(
          decoration: const pw.BoxDecoration(color: _primary),
          children: [
            _th('SR', pw.TextAlign.center),
            _th('PRODUCT', pw.TextAlign.left),
            _th('WT.', pw.TextAlign.center),
            _th('PACKETS', pw.TextAlign.right),
            _th('PRICE/PKT', pw.TextAlign.right),
            _th('RETURNED AMT.', pw.TextAlign.right),
            _th('ORIGINAL VALUE', pw.TextAlign.right),
            _th('NET SALE (THIS ITEM)', pw.TextAlign.right),
          ],
        ),
        ...lines.asMap().entries.map((entry) {
          final int index = entry.key;
          final ReturnSlipLine line = entry.value;
          final ReturnOrderItemModel item = line.item;
          final PdfColor bg = index.isEven ? _white : _tintSoft;
          // "20 x 1.5 kg": packets per bag times the bag's own weight, the
          // packaging the order itself sold -- shown only when a matching
          // order line was found, since an unmatched return has no bag count
          // to report, only the packet weight already in its own column.
          final OrderPackagingModel? packaging = line.matchedPackaging;
          final String? packagingLabel = packaging == null
              ? null
              : '${packaging.packets} x ${item.packetWeightLabel}';

          return pw.TableRow(
            decoration: pw.BoxDecoration(color: bg),
            children: [
              _td('${index + 1}', pw.TextAlign.center),
              pw.Padding(
                padding: const pw.EdgeInsets.symmetric(
                  horizontal: 6,
                  vertical: 5,
                ),
                child: pw.Column(
                  crossAxisAlignment: pw.CrossAxisAlignment.start,
                  children: [
                    pw.Text(
                      item.product.name.isEmpty ? _blank : item.product.name,
                      style: pw.TextStyle(
                        fontSize: 7.5,
                        fontWeight: pw.FontWeight.bold,
                        color: _textPrimary,
                      ),
                    ),
                    if (packagingLabel != null) ...[
                      pw.SizedBox(height: 1),
                      pw.Text(
                        packagingLabel,
                        style: const pw.TextStyle(
                          fontSize: 6.3,
                          color: _textMuted,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              _td(item.packetWeightLabel, pw.TextAlign.center),
              _tdBold('${item.packets}', pw.TextAlign.right),
              _td(_amount(item.pricePerPacket), pw.TextAlign.right),
              _tdBold(_amount(item.lineTotal), pw.TextAlign.right),
              _td(
                line.originalLineTotal == null
                    ? _blank
                    : _amount(line.originalLineTotal!),
                pw.TextAlign.right,
              ),
              _netSaleCell(line.netSale),
            ],
          );
        }),
      ],
    );
  }

  static pw.Widget _th(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 5, vertical: 6),
      child: pw.Text(
        text,
        textAlign: align,
        style: pw.TextStyle(
          fontSize: 6.3,
          fontWeight: pw.FontWeight.bold,
          color: _white,
          letterSpacing: 0.2,
        ),
      ),
    );
  }

  static pw.Widget _td(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 5),
      child: pw.Text(
        text.isEmpty ? _blank : text,
        textAlign: align,
        style: const pw.TextStyle(fontSize: 7.5, color: _textPrimary),
      ),
    );
  }

  static pw.Widget _tdBold(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 5),
      child: pw.Text(
        text.isEmpty ? _blank : text,
        textAlign: align,
        style: pw.TextStyle(
          fontSize: 7.5,
          fontWeight: pw.FontWeight.bold,
          color: _textPrimary,
        ),
      ),
    );
  }

  /// The one figure this document exists to add, so it is always bold and
  /// always in the brand green -- even a negative net (the return was worth
  /// more than what is left of that line) stays green rather than reading as
  /// an error state; a return is a normal outcome, not a fault.
  static pw.Widget _netSaleCell(num? net) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 5),
      child: pw.Text(
        net == null ? _blank : _amount(net),
        textAlign: pw.TextAlign.right,
        style: pw.TextStyle(
          fontSize: 7.5,
          fontWeight: pw.FontWeight.bold,
          color: net == null ? _textMuted : _primaryDark,
        ),
      ),
    );
  }

  /// Printed once under the table rather than on every row: the NET SALE
  /// column reads like a running figure until it is told otherwise, so the
  /// slip says in words what the header already says in short -- this
  /// column, like RETURNED AMT. and ORIGINAL VALUE beside it, is this one
  /// item's own figure, not a cumulative total.
  static pw.Widget _netSaleNote() {
    return pw.Text(
      'Net sale is for this item only -- what the line was worth before the '
      'return, less what was returned.',
      style: pw.TextStyle(
        fontSize: 6.3,
        fontStyle: pw.FontStyle.italic,
        color: _textMuted,
      ),
    );
  }

  // ══════════════ TOTALS ══════════════

  static pw.Widget _totalsRow(
    List<ReturnSlipLine> lines,
    ReturnOrderModel returnOrder,
  ) {
    final num totalNetSale = lines.fold<num>(
      0,
      (sum, line) => sum + (line.netSale ?? 0),
    );
    final bool hasUnmatched = lines.any((line) => line.originalLineTotal == null);

    return pw.Row(
      mainAxisAlignment: pw.MainAxisAlignment.end,
      children: [
        pw.Container(
          width: 260,
          decoration: pw.BoxDecoration(
            border: pw.Border.all(color: _divider, width: _hairline),
            borderRadius: pw.BorderRadius.circular(3),
          ),
          child: pw.Column(
            children: [
              _totalLine('Total Items', '${returnOrder.items.length}'),
              _totalLine(
                'Total KG',
                '${_trim(returnOrder.totalKg)} kg',
              ),
              _totalLine('Total Packets', '${returnOrder.totalPackets}'),
              _totalLine(
                'Total Returned Amount',
                _amount(returnOrder.totalAmount),
              ),
              _totalLine(
                hasUnmatched
                    ? 'Total Net Sale (partial)'
                    : 'Total Net Sale (after this return)',
                _amount(totalNetSale),
                isEmphasis: true,
              ),
            ],
          ),
        ),
      ],
    );
  }

  static pw.Widget _totalLine(
    String label,
    String value, {
    bool isEmphasis = false,
  }) {
    return pw.Container(
      color: isEmphasis ? _tintStrong : _white,
      padding: const pw.EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(
            label,
            style: pw.TextStyle(
              fontSize: 7.5,
              fontWeight: pw.FontWeight.bold,
              color: isEmphasis ? _primaryDark : _textSecondary,
            ),
          ),
          pw.Text(
            value,
            style: pw.TextStyle(
              fontSize: isEmphasis ? 8.5 : 7.5,
              fontWeight: pw.FontWeight.bold,
              color: isEmphasis ? _primaryDark : _textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  // ══════════════ FOOTER ══════════════

  static pw.Widget _footer(pw.Context context) {
    return pw.Padding(
      padding: const pw.EdgeInsets.only(top: 8),
      child: pw.Row(
        mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
        children: [
          pw.Text(
            'This is a computer generated document.',
            style: pw.TextStyle(
              fontSize: 6.5,
              fontStyle: pw.FontStyle.italic,
              color: _textMuted,
            ),
          ),
          pw.Text(
            'Page ${context.pageNumber} of ${context.pagesCount}',
            style: const pw.TextStyle(fontSize: 6.5, color: _textMuted),
          ),
        ],
      ),
    );
  }

  static String _date(DateTime? value) =>
      value == null ? _blank : DateFormatter.dayLabel(value);

  static String _amount(num value) => 'Rs. ${value.toStringAsFixed(2)}';

  static String _trim(num value) {
    if (value == value.roundToDouble()) return value.toInt().toString();
    return value.toString();
  }
}
