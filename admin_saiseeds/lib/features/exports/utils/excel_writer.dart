import 'dart:typed_data';

import 'package:excel/excel.dart';

import 'export_sheets.dart';

/// Writes a flattened [ExportSheet] to real .xlsx bytes.
class ExcelWriter {
  ExcelWriter._();

  static const String mimeType =
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

  /// Excel caps a sheet name at 31 characters and rejects : \ / ? * [ ].
  static const int _maxSheetName = 31;

  static final ExcelColor _headerFill = '#1E7A34'.excelColor;
  static final ExcelColor _bandFill = '#EDF4EE'.excelColor;
  static final ExcelColor _ruleColor = '#B9CDBE'.excelColor;

  static Uint8List build({
    required String sheetName,
    required ExportSheet sheet,
  }) {
    final Excel excel = Excel.createExcel();
    final String name = _safeName(sheetName);

    excel.rename(excel.getDefaultSheet()!, name);
    final Sheet target = excel[name];

    target.appendRow([
      for (final String header in sheet.headers) TextCellValue(header),
    ]);

    // displayRows blanks a continuation row's repeated parent columns, so
    // a multi-item record reads as one block.
    for (final List<String> row in sheet.displayRows) {
      target.appendRow([for (final String cell in row) _cell(cell)]);
    }

    _style(target, sheet);
    target.setColumnAutoFit(0);

    final List<int>? encoded = excel.encode();
    if (encoded == null) {
      throw StateError('The spreadsheet could not be encoded.');
    }
    return Uint8List.fromList(encoded);
  }

  /// Banding and rules so a record spanning several lines reads as one
  /// block: alternate records are tinted, and every record opens with a
  /// rule above its first line.
  static void _style(Sheet target, ExportSheet sheet) {
    final Border rule = Border(
      borderColorHex: _ruleColor,
      borderStyle: BorderStyle.Thin,
    );

    for (int column = 0; column < sheet.headers.length; column++) {
      target
          .cell(CellIndex.indexByColumnRow(columnIndex: column, rowIndex: 0))
          .cellStyle = CellStyle(
        bold: true,
        fontColorHex: ExcelColor.white,
        backgroundColorHex: _headerFill,
        bottomBorder: rule,
      );
    }

    final List<int> groups = sheet.groupIndices;

    for (int row = 0; row < sheet.rows.length; row++) {
      final bool isTinted = groups[row].isOdd;
      final bool opensGroup = row == 0 || groups[row] != groups[row - 1];

      for (int column = 0; column < sheet.headers.length; column++) {
        target
            .cell(
              CellIndex.indexByColumnRow(
                columnIndex: column,
                rowIndex: row + 1,
              ),
            )
            .cellStyle = CellStyle(
          backgroundColorHex: isTinted ? _bandFill : ExcelColor.none,
          topBorder: opensGroup ? rule : null,
        );
      }
    }
  }

  /// Numbers are written as numbers so a spreadsheet can total a column;
  /// anything else stays text, which keeps ids and lot numbers intact.
  static CellValue _cell(String raw) {
    if (raw.isEmpty) return TextCellValue('');

    final int? asInt = int.tryParse(raw);
    if (asInt != null) return IntCellValue(asInt);

    final double? asDouble = double.tryParse(raw);
    if (asDouble != null) return DoubleCellValue(asDouble);

    return TextCellValue(raw);
  }

  static String _safeName(String raw) {
    final String cleaned = raw.replaceAll(RegExp(r'[:\\/?*\[\]]'), ' ').trim();
    final String fallback = cleaned.isEmpty ? 'Export' : cleaned;
    return fallback.length <= _maxSheetName
        ? fallback
        : fallback.substring(0, _maxSheetName);
  }
}
