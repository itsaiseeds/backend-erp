import 'dart:typed_data';

import 'package:archive/archive.dart';

import '../../dispatch_challans/data/models/dispatch_challan_model.dart';
import '../../dispatch_challans/utils/challan_generator.dart';

/// Bundles one challan PDF per dispatch into a single zip.
///
/// The PDFs are the same documents the Dispatch Orders tab produces, so a
/// bundled receipt and a singly downloaded one are byte-for-byte the same
/// layout.
class ChallanZipWriter {
  ChallanZipWriter._();

  static const String mimeType = 'application/zip';

  static Future<Uint8List> build(List<DispatchChallanModel> challans) async {
    final Archive archive = Archive();
    final Set<String> used = {};

    for (final DispatchChallanModel challan in challans) {
      final Uint8List pdf = await ChallanGenerator.generate(challan);
      final String name = _uniqueName(challan, used);
      archive.addFile(ArchiveFile(name, pdf.length, pdf));
    }

    final List<int>? encoded = ZipEncoder().encode(archive);
    if (encoded == null) {
      throw StateError('The archive could not be encoded.');
    }
    return Uint8List.fromList(encoded);
  }

  /// Two challans can share a reference if the API ever repeats one, and a
  /// zip with duplicate entries extracts unpredictably -- so a clash gets a
  /// numeric suffix rather than silently overwriting.
  static String _uniqueName(DispatchChallanModel challan, Set<String> used) {
    final String stem = _safeStem(challan.fileReference);
    String name = '$stem.pdf';
    int suffix = 2;

    while (!used.add(name)) {
      name = '$stem-$suffix.pdf';
      suffix++;
    }

    return name;
  }

  static String _safeStem(String raw) {
    final String cleaned = raw.trim().replaceAll(RegExp(r'[\\/:*?"<>|]'), '-');
    return cleaned.isEmpty ? 'challan' : cleaned;
  }
}
