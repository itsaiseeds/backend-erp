import 'package:flutter/services.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';
import '../../../core/constants/app_strings.dart';
import '../../../core/utils/formatters/date_formatter.dart';
import '../data/models/dispatch_challan_model.dart';

/// Renders one dispatch challan to a printable A4 sheet.
///
/// Type scale and table construction follow the SanturoPolyfab invoice so the
/// two documents read as one house style: 7.5 body, 7 table heads, 6.5 fine
/// print, 14 document title, 18 company name.
class ChallanGenerator {
  ChallanGenerator._();

  // The sheet is mostly white with green used only to structure it, so a
  // printed challan does not drink ink the way a solid header would.
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

  /// ASCII on purpose: the Helvetica fallback carries no em-dash glyph, so a
  /// nicer character would silently drop out when the font download fails.
  static const String _blank = '-';

  static Future<Uint8List> generate(DispatchChallanModel challan) async {
    final pw.Font base = await PdfGoogleFonts.interRegular();
    final pw.Font bold = await PdfGoogleFonts.interBold();
    final pw.Font italic = await PdfGoogleFonts.interItalic();

    final pw.Document doc = pw.Document(
      theme: pw.ThemeData.withFont(base: base, bold: bold, italic: italic),
    );

    final pw.MemoryImage? logo = await _loadLogo();

    doc.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        header: (context) => context.pageNumber == 1
            ? pw.SizedBox()
            : pw.Padding(
                padding: const pw.EdgeInsets.only(bottom: 10),
                child: _continuationHeader(challan),
              ),
        footer: (context) => pw.Column(
          crossAxisAlignment: pw.CrossAxisAlignment.stretch,
          mainAxisSize: pw.MainAxisSize.min,
          children: [
            if (context.pageNumber == context.pagesCount) ...[
              _declaration(challan),
              pw.SizedBox(height: 14),
              _signatures(challan),
              pw.SizedBox(height: 8),
            ],
            _footer(context),
          ],
        ),
        build: (context) => [
          _header(challan, logo),
          pw.SizedBox(height: 12),
          _partyRow(challan),
          pw.SizedBox(height: 10),
          _journeyStrip(challan),
          pw.SizedBox(height: 12),
          _itemsTable(challan),
          pw.SizedBox(height: 10),
          _totalsRow(challan),
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

  static pw.Widget _header(DispatchChallanModel challan, pw.MemoryImage? logo) {
    final ChallanCompanyModel? us = challan.ourDetails;
    final ChallanDispatchModel? dispatch = challan.dispatch;

    final String taxLine = [
      if ((us?.gstNumber ?? '').isNotEmpty) 'GSTIN: ${us!.gstNumber}',
      if ((us?.stateName ?? '').isNotEmpty) 'State: ${us!.stateName}',
      'HSN: ${challan.hsnCode}',
    ].join('   |   ');

    // Kept off the tax line so neither wraps on a narrow company name.
    final String reachLine = [
      if ((us?.contactNumber ?? '').isNotEmpty) 'Ph: ${us!.contactNumber}',
      if ((us?.email ?? '').isNotEmpty) us!.email,
      if ((us?.web ?? '').isNotEmpty) us!.web,
    ].join('   |   ');

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
                    (us?.companyName ?? '').isEmpty
                        ? AppStrings.APP_TAGLINE
                        : us!.companyName,
                    style: pw.TextStyle(
                      fontSize: 18,
                      fontWeight: pw.FontWeight.bold,
                      color: _primary,
                    ),
                  ),
                  if ((us?.companyAddress ?? '').isNotEmpty) ...[
                    pw.SizedBox(height: 2),
                    pw.Text(
                      us!.companyAddress,
                      style: const pw.TextStyle(
                        fontSize: 7.5,
                        color: _textSecondary,
                        lineSpacing: 1.2,
                      ),
                    ),
                  ],
                  pw.SizedBox(height: 2),
                  pw.Text(
                    taxLine,
                    style: const pw.TextStyle(fontSize: 7, color: _textMuted),
                  ),
                  if (reachLine.isNotEmpty) ...[
                    pw.SizedBox(height: 1),
                    pw.Text(
                      reachLine,
                      style: const pw.TextStyle(fontSize: 7, color: _primary),
                    ),
                  ],
                ],
              ),
            ),
            pw.SizedBox(width: 10),
            pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.end,
              children: [
                pw.Text(
                  'DELIVERY CHALLAN',
                  style: pw.TextStyle(
                    fontSize: 14,
                    fontWeight: pw.FontWeight.bold,
                    color: _primaryDark,
                    letterSpacing: 1.4,
                  ),
                ),
                pw.SizedBox(height: 5),
                _kv('Challan No:', challan.challanNumber),
                _kv('Order No:', challan.orderPublicId),
                _kv('Date:', _date(dispatch?.dispatchDateTime)),
                _kv('F.Y.:', challan.financialYear),
              ],
            ),
          ],
        ),
        pw.SizedBox(height: 8),
        pw.Container(height: 2, color: _primary),
      ],
    );
  }

  static pw.Widget _continuationHeader(DispatchChallanModel challan) {
    return pw.Column(
      children: [
        pw.Row(
          mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
          children: [
            pw.Text(
              'DELIVERY CHALLAN  ${challan.challanNumber}',
              style: pw.TextStyle(
                fontSize: 8,
                fontWeight: pw.FontWeight.bold,
                color: _primaryDark,
              ),
            ),
            pw.Text(
              challan.receiverName,
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

  // ══════════════ PARTIES ══════════════

  static pw.Widget _partyRow(DispatchChallanModel challan) {
    return pw.Row(
      crossAxisAlignment: pw.CrossAxisAlignment.start,
      children: [
        pw.Expanded(
          child: _partyCard(
            title: 'CONSIGNEE (SHIP TO)',
            name: challan.receiverName,
            lines: [
              if (challan.receiverAddress.isNotEmpty) challan.receiverAddress,
            ],
            pairs: [
              if (challan.receiverGst.isNotEmpty)
                ['GSTIN', challan.receiverGst],
              if (challan.contactSummary.isNotEmpty)
                ['Contact', challan.contactSummary],
            ],
          ),
        ),
        pw.SizedBox(width: 10),
        pw.Expanded(
          child: _partyCard(
            title: 'DISPATCH DETAILS',
            name: '',
            lines: const [],
            pairs: [
              ['LR No.', challan.dispatch?.lrNumber ?? ''],
              ['Transport', _transportLabel(challan.dispatch)],
              ['Vehicle', challan.dispatch?.vehicleNumber ?? ''],
              ['Driver', challan.driverSummary],
            ],
          ),
        ),
      ],
    );
  }

  static String _transportLabel(ChallanDispatchModel? dispatch) =>
      dispatch?.transportLabel ?? '';

  static pw.Widget _partyCard({
    required String title,
    required String name,
    required List<String> lines,
    required List<List<String>> pairs,
  }) {
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
              title,
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
                if (name.isNotEmpty)
                  pw.Text(
                    name,
                    style: pw.TextStyle(
                      fontSize: 9,
                      fontWeight: pw.FontWeight.bold,
                      color: _textPrimary,
                    ),
                  ),
                for (final String line in lines) ...[
                  pw.SizedBox(height: 2),
                  pw.Text(
                    line,
                    style: const pw.TextStyle(
                      fontSize: 7.5,
                      color: _textSecondary,
                      lineSpacing: 1.3,
                    ),
                  ),
                ],
                for (final List<String> pair in pairs) ...[
                  pw.SizedBox(height: 3),
                  _inlinePair(pair.first, pair.last),
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

  // ══════════════ JOURNEY ══════════════

  static pw.Widget _journeyStrip(DispatchChallanModel challan) {
    final ChallanDispatchModel? dispatch = challan.dispatch;

    return pw.Container(
      decoration: pw.BoxDecoration(
        color: _tintSoft,
        border: pw.Border.all(color: _divider, width: _hairline),
        borderRadius: pw.BorderRadius.circular(3),
      ),
      padding: const pw.EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: pw.Row(
        children: [
          _journeyCell('FROM', dispatch?.fromCity ?? ''),
          pw.Container(width: 1, height: 18, color: _divider),
          _journeyCell('TO', dispatch?.toCity ?? ''),
          pw.Container(width: 1, height: 18, color: _divider),
          _journeyCell('DISPATCHED', _date(dispatch?.dispatchDateTime)),
          pw.Container(width: 1, height: 18, color: _divider),
          _journeyCell('HSN / SAC', challan.hsnCode),
        ],
      ),
    );
  }

  static pw.Widget _journeyCell(String label, String value) {
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

  static pw.Widget _itemsTable(DispatchChallanModel challan) {
    return pw.Table(
      border: pw.TableBorder.all(color: _divider, width: _hairline),
      columnWidths: const {
        0: pw.FixedColumnWidth(26),
        1: pw.FlexColumnWidth(),
        2: pw.FixedColumnWidth(78),
        3: pw.FixedColumnWidth(54),
        4: pw.FixedColumnWidth(52),
        5: pw.FixedColumnWidth(62),
        6: pw.FixedColumnWidth(38),
      },
      children: [
        pw.TableRow(
          decoration: const pw.BoxDecoration(color: _primary),
          children: [
            _th('SR', pw.TextAlign.center),
            _th('DESCRIPTION OF GOODS', pw.TextAlign.left),
            _th('LOT NO.', pw.TextAlign.left),
            _th('PACKING', pw.TextAlign.center),
            _th('PACKETS', pw.TextAlign.right),
            _th('TOTAL WT.', pw.TextAlign.right),
            _th('BAGS', pw.TextAlign.right),
          ],
        ),
        ...challan.items.asMap().entries.map((entry) {
          final int index = entry.key;
          final ChallanItemModel item = entry.value;
          final PdfColor bg = index.isEven ? _white : _tintSoft;

          return pw.TableRow(
            decoration: pw.BoxDecoration(color: bg),
            children: [
              _td('${index + 1}', pw.TextAlign.center),
              pw.Padding(
                padding: const pw.EdgeInsets.symmetric(
                  horizontal: 6,
                  vertical: 5,
                ),
                child: pw.Text(
                  item.productName.isEmpty ? _blank : item.productName,
                  style: pw.TextStyle(
                    fontSize: 7.5,
                    fontWeight: pw.FontWeight.bold,
                    color: _textPrimary,
                  ),
                ),
              ),
              _td(item.lotNumber, pw.TextAlign.left),
              _td('${item.packetWeight} kg', pw.TextAlign.center),
              _tdBold('${item.shippedPackets}', pw.TextAlign.right),
              _td(
                item.shippedWeight.isEmpty
                    ? _blank
                    : '${item.shippedWeight} kg',
                pw.TextAlign.right,
              ),
              _td(
                item.hasBags ? '${item.quantity}' : _blank,
                pw.TextAlign.right,
              ),
            ],
          );
        }),
      ],
    );
  }

  static pw.Widget _th(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 6),
      child: pw.Text(
        text,
        textAlign: align,
        style: pw.TextStyle(
          fontSize: 7,
          fontWeight: pw.FontWeight.bold,
          color: _white,
          letterSpacing: 0.3,
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

  // ══════════════ TOTALS ══════════════

  static pw.Widget _totalsRow(DispatchChallanModel challan) {
    final int totalBags = challan.items.fold(
      0,
      (sum, item) => sum + item.quantity,
    );

    final double totalWeight = challan.items.fold<double>(
      0,
      (sum, item) => sum + (double.tryParse(item.shippedWeight) ?? 0),
    );

    return pw.Row(
      mainAxisAlignment: pw.MainAxisAlignment.end,
      children: [
        pw.Container(
          width: 240,
          decoration: pw.BoxDecoration(
            border: pw.Border.all(color: _divider, width: _hairline),
            borderRadius: pw.BorderRadius.circular(3),
          ),
          child: pw.Column(
            children: [
              _totalLine('Total Items', '${challan.itemCount}'),
              _totalLine(
                'Total Weight',
                '${totalWeight.toStringAsFixed(3)} kg',
              ),
              _totalLine('Total Bags', '$totalBags'),
              _totalLine(
                'Total Packets',
                '${challan.totalPackets}',
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

  // ══════════════ DECLARATION ══════════════

  static pw.Widget _declaration(DispatchChallanModel challan) {
    final String licenceNumber = challan.ourDetails?.seedsLicenceNumber ?? '';

    return pw.Container(
      width: double.infinity,
      decoration: pw.BoxDecoration(
        color: _tintSoft,
        border: pw.Border.all(color: _divider, width: _hairline),
        borderRadius: pw.BorderRadius.circular(3),
      ),
      padding: const pw.EdgeInsets.fromLTRB(10, 7, 10, 8),
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(
            'DECLARATION',
            style: pw.TextStyle(
              fontSize: 7,
              fontWeight: pw.FontWeight.bold,
              color: _primaryDark,
              letterSpacing: 0.8,
            ),
          ),
          pw.SizedBox(height: 3),
          pw.Text(
            'Received the above mentioned material in good condition and order. '
            'Seeds are exempted in the G.S.T. rate schedule, HSN code '
            '${challan.hsnCode}, for sowing purpose only.',
            style: const pw.TextStyle(
              fontSize: 6.5,
              color: _textSecondary,
              lineSpacing: 1.4,
            ),
          ),
          if (licenceNumber.isNotEmpty) ...[
            pw.SizedBox(height: 4),
            _inlinePair(
              'Seeds Licence No',
              licenceNumber,
              labelWidth: 86,
            ),
          ],
        ],
      ),
    );
  }

  // ══════════════ SIGNATURES ══════════════

  static pw.Widget _signatures(DispatchChallanModel challan) {
    final String company = challan.ourDetails?.companyName ?? '';

    return pw.Row(
      crossAxisAlignment: pw.CrossAxisAlignment.end,
      children: [
        pw.Expanded(child: _signatureBlock('Receiver Signature', '')),
        pw.SizedBox(width: 40),
        pw.Expanded(
          child: _signatureBlock(
            'Authorised Signatory',
            company.isEmpty ? '' : 'For $company',
            isEnd: true,
          ),
        ),
      ],
    );
  }

  static pw.Widget _signatureBlock(
    String label,
    String caption, {
    bool isEnd = false,
  }) {
    return pw.Column(
      crossAxisAlignment: isEnd
          ? pw.CrossAxisAlignment.end
          : pw.CrossAxisAlignment.start,
      children: [
        if (caption.isNotEmpty) ...[
          pw.Text(
            caption,
            style: pw.TextStyle(
              fontSize: 7.5,
              fontWeight: pw.FontWeight.bold,
              color: _textPrimary,
            ),
          ),
          pw.SizedBox(height: 26),
        ] else
          pw.SizedBox(height: 36),
        pw.Container(height: _hairline, width: 150, color: _textMuted),
        pw.SizedBox(height: 3),
        pw.Text(
          label,
          style: const pw.TextStyle(fontSize: 7, color: _textMuted),
        ),
      ],
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

  // DateFormatter falls back to an em-dash, which the Helvetica fallback
  // cannot draw, so an absent date resolves to the ASCII placeholder here.
  static String _date(DateTime? value) =>
      value == null ? _blank : DateFormatter.dayLabel(value);
}
