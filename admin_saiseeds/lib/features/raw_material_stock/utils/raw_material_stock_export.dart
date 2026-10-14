import 'dart:typed_data';
import '../../../core/utils/download/file_download.dart';
import '../../exports/utils/export_sheets.dart';
import '../../exports/utils/excel_writer.dart';
import '../data/models/raw_material_stock_model.dart';

/// Builds and downloads the raw-material stock table exactly as loaded on
/// screen -- every column the table carries, not just the ones currently
/// visible, since the sheet has no "scroll for more" limit a browser does.
class RawMaterialStockExport {
  RawMaterialStockExport._();

  static const List<String> _headers = [
    'Product',
    'Incoming (kg)',
    'Packed (kg)',
    'Wasted (kg)',
    'Waste Reserved (kg)',
    'Waste Consumed (kg)',
    'Waste Available (kg)',
    'Rejected (kg)',
    'Available (kg)',
  ];

  static List<String> _rowOf(RawMaterialStockLineModel line) => [
    line.name,
    line.incomingKg,
    line.packedKg,
    line.wastedKg,
    line.wasteReservedKg,
    line.wasteConsumedKg,
    line.wasteAvailableKg,
    line.rejectedKg,
    line.availableKg,
  ];

  static ExportSheet buildSheet(List<RawMaterialStockLineModel> lines) {
    return ExportSheet(
      headers: _headers,
      rows: [for (final RawMaterialStockLineModel line in lines) _rowOf(line)],
    );
  }

  /// `true` if a file was actually handed to the browser; `false` for an
  /// empty table, which downloads nothing rather than a headers-only sheet.
  static Future<bool> download({
    required List<RawMaterialStockLineModel> lines,
    required String asOf,
  }) async {
    final ExportSheet sheet = buildSheet(lines);
    if (sheet.isEmpty) return false;

    final Uint8List bytes = ExcelWriter.build(
      sheetName: 'Raw Material',
      sheet: sheet,
    );

    final String suffix = asOf.trim().isEmpty ? '' : '_$asOf';
    await downloadBytes(
      bytes: bytes,
      fileName: 'raw-material-stock$suffix.xlsx',
      mimeType: ExcelWriter.mimeType,
    );
    return true;
  }
}
