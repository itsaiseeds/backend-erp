import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

/// Hands [bytes] to the user as a file named [fileName].
///
/// The bytes are wrapped in a Blob and offered through a synthetic anchor
/// click, which is the only way to start a download from a Flutter web
/// canvas. The object URL is revoked straight after so the blob is freed.
Future<void> downloadBytes({
  required Uint8List bytes,
  required String fileName,
  required String mimeType,
}) async {
  final web.Blob blob = web.Blob(
    <JSUint8Array>[bytes.toJS].toJS,
    web.BlobPropertyBag(type: mimeType),
  );

  final String url = web.URL.createObjectURL(blob);

  final web.HTMLAnchorElement anchor =
      web.document.createElement('a') as web.HTMLAnchorElement
        ..href = url
        ..download = fileName
        ..style.display = 'none';

  web.document.body?.appendChild(anchor);
  anchor.click();
  anchor.remove();

  web.URL.revokeObjectURL(url);
}
