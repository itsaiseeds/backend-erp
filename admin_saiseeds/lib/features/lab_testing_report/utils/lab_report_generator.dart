import 'package:flutter/services.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:printing/printing.dart';

import '../../../core/utils/formatters/date_formatter.dart';
import '../data/models/lab_testing_report_model.dart';

/// Renders a window of lab tests to a printable A4 report.
///
/// Same house style as [ChallanGenerator] (dispatch_challans) -- the two
/// documents this app prints should read as one family -- and mirrored
/// byte-for-byte by the lab tester's own app, so a report downloaded from
/// here and one shared from the mobile app are the same document.
class LabReportGenerator {
  LabReportGenerator._();

  static const PdfColor _primary = PdfColor.fromInt(0xFF1E7A34);
  static const PdfColor _primaryDark = PdfColor.fromInt(0xFF145523);
  static const PdfColor _tintSoft = PdfColor.fromInt(0xFFF4F9F5);
  static const PdfColor _textPrimary = PdfColor.fromInt(0xFF111111);
  static const PdfColor _textSecondary = PdfColor.fromInt(0xFF555555);
  static const PdfColor _textMuted = PdfColor.fromInt(0xFF999999);
  static const PdfColor _divider = PdfColor.fromInt(0xFFDCE0DC);
  static const PdfColor _white = PdfColor.fromInt(0xFFFFFFFF);
  static const PdfColor _success = PdfColor.fromInt(0xFF1E7A34);
  static const PdfColor _error = PdfColor.fromInt(0xFFB3261E);

  static const double _hairline = 0.5;
  static const String _blank = '-';

  static Future<Uint8List> generate({
    required String startDate,
    required String endDate,
    required List<LabTestingReportModel> results,
  }) async {
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
                child: _continuationHeader(startDate, endDate),
              ),
        footer: (context) => _footer(context),
        build: (context) => [
          _header(logo, startDate, endDate, results.length),
          pw.SizedBox(height: 12),
          _summaryRow(results),
          pw.SizedBox(height: 12),
          _resultsTable(results),
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

  static pw.Widget _header(
    pw.MemoryImage? logo,
    String startDate,
    String endDate,
    int count,
  ) {
    return pw.Column(
      children: [
        pw.Row(
          crossAxisAlignment: pw.CrossAxisAlignment.center,
          children: [
            if (logo != null) ...[
              pw.Image(logo, width: 44, height: 44),
              pw.SizedBox(width: 10),
            ],
            pw.Expanded(
              child: pw.Text(
                'Saiseeds Company',
                style: pw.TextStyle(
                  fontSize: 16,
                  fontWeight: pw.FontWeight.bold,
                  color: _primary,
                ),
              ),
            ),
            pw.SizedBox(width: 10),
            pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.end,
              children: [
                pw.Text(
                  'LAB TESTING REPORT',
                  style: pw.TextStyle(
                    fontSize: 14,
                    fontWeight: pw.FontWeight.bold,
                    color: _primaryDark,
                    letterSpacing: 1.2,
                  ),
                ),
                pw.SizedBox(height: 5),
                _kv('Window:', '$startDate  to  $endDate'),
                _kv('Tests:', '$count'),
              ],
            ),
          ],
        ),
        pw.SizedBox(height: 8),
        pw.Container(height: 2, color: _primary),
      ],
    );
  }

  static pw.Widget _continuationHeader(String startDate, String endDate) {
    return pw.Column(
      children: [
        pw.Row(
          mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
          children: [
            pw.Text(
              'LAB TESTING REPORT',
              style: pw.TextStyle(
                fontSize: 8,
                fontWeight: pw.FontWeight.bold,
                color: _primaryDark,
              ),
            ),
            pw.Text(
              '$startDate to $endDate',
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

  // ══════════════ SUMMARY ══════════════

  static pw.Widget _summaryRow(List<LabTestingReportModel> results) {
    final int passed = results.where((test) => test.isPass).length;
    final int failed = results.where((test) => test.isFail).length;
    final int pending = results.length - passed - failed;

    return pw.Container(
      decoration: pw.BoxDecoration(
        color: _tintSoft,
        border: pw.Border.all(color: _divider, width: _hairline),
        borderRadius: pw.BorderRadius.circular(3),
      ),
      padding: const pw.EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: pw.Row(
        children: [
          _summaryCell('TOTAL', '${results.length}', _textPrimary),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell('PASSED', '$passed', _success),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell('FAILED', '$failed', _error),
          pw.Container(width: 1, height: 18, color: _divider),
          _summaryCell('PENDING', '$pending', _textMuted),
        ],
      ),
    );
  }

  static pw.Widget _summaryCell(String label, String value, PdfColor tone) {
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
              value,
              style: pw.TextStyle(
                fontSize: 9,
                fontWeight: pw.FontWeight.bold,
                color: tone,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ══════════════ RESULTS TABLE ══════════════

  static pw.Widget _resultsTable(List<LabTestingReportModel> results) {
    return pw.Table(
      border: pw.TableBorder.all(color: _divider, width: _hairline),
      columnWidths: const {
        0: pw.FixedColumnWidth(24),
        1: pw.FlexColumnWidth(1.3),
        2: pw.FlexColumnWidth(1.1),
        3: pw.FixedColumnWidth(50),
        4: pw.FixedColumnWidth(34),
        5: pw.FixedColumnWidth(34),
        6: pw.FixedColumnWidth(30),
        7: pw.FixedColumnWidth(48),
        8: pw.FixedColumnWidth(48),
        9: pw.FixedColumnWidth(36),
        10: pw.FlexColumnWidth(1),
      },
      children: [
        pw.TableRow(
          decoration: const pw.BoxDecoration(color: _primary),
          children: [
            _th('SR', pw.TextAlign.center),
            _th('PRODUCT', pw.TextAlign.left),
            _th('PARTY', pw.TextAlign.left),
            _th('LOT NO.', pw.TextAlign.left),
            _th('PLANTS', pw.TextAlign.right),
            _th('FEMALE', pw.TextAlign.right),
            _th('OT', pw.TextAlign.right),
            _th('IMPURITY %', pw.TextAlign.right),
            _th('GOT %', pw.TextAlign.right),
            _th('RESULT', pw.TextAlign.center),
            _th('TESTED BY / AT', pw.TextAlign.left),
          ],
        ),
        ...results.asMap().entries.map((entry) {
          final int index = entry.key;
          final LabTestingReportModel test = entry.value;
          final PdfColor bg = index.isEven ? _white : _tintSoft;

          return pw.TableRow(
            decoration: pw.BoxDecoration(color: bg),
            children: [
              _td('${index + 1}', pw.TextAlign.center),
              _tdBold(test.productName),
              _td(test.partyName, pw.TextAlign.left),
              _td(test.lotNo, pw.TextAlign.left),
              _td('${test.numberOfPlants}', pw.TextAlign.right),
              _td('${test.femaleCount}', pw.TextAlign.right),
              _td('${test.otCount}', pw.TextAlign.right),
              _td(_percent(test.geneticalImpurity), pw.TextAlign.right),
              _td(_percent(test.growOutTest), pw.TextAlign.right),
              _resultCell(test.result),
              _td(
                '${test.testedByName}\n${DateFormatter.label(test.testedAt)}',
                pw.TextAlign.left,
              ),
            ],
          );
        }),
      ],
    );
  }

  static pw.Widget _th(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 6),
      child: pw.Text(
        text,
        textAlign: align,
        style: pw.TextStyle(
          fontSize: 6,
          fontWeight: pw.FontWeight.bold,
          color: _white,
          letterSpacing: 0.2,
        ),
      ),
    );
  }

  static pw.Widget _td(String text, pw.TextAlign align) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 5),
      child: pw.Text(
        text.isEmpty ? _blank : text,
        textAlign: align,
        style: const pw.TextStyle(fontSize: 6.5, color: _textPrimary),
      ),
    );
  }

  static pw.Widget _tdBold(String text) {
    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 5),
      child: pw.Text(
        text.isEmpty ? _blank : text,
        style: pw.TextStyle(
          fontSize: 6.5,
          fontWeight: pw.FontWeight.bold,
          color: _textPrimary,
        ),
      ),
    );
  }

  static pw.Widget _resultCell(String result) {
    final String normalized = result.toLowerCase();
    final PdfColor tone = normalized == 'pass'
        ? _success
        : normalized == 'fail'
        ? _error
        : _textMuted;

    return pw.Padding(
      padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 5),
      child: pw.Text(
        result.isEmpty ? _blank : result,
        textAlign: pw.TextAlign.center,
        style: pw.TextStyle(
          fontSize: 6.5,
          fontWeight: pw.FontWeight.bold,
          color: tone,
        ),
      ),
    );
  }

  static String _percent(String value) {
    final String trimmed = value.trim();
    return trimmed.isEmpty ? '' : '$trimmed%';
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
}
