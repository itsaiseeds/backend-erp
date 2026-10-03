import 'dart:typed_data';

/// Hands [bytes] to the user as a file named [fileName].
///
/// Only the web implementation does real work; the stub keeps the admin
/// portal compiling for other targets, which it is never shipped to.
Future<void> downloadBytes({
  required Uint8List bytes,
  required String fileName,
  required String mimeType,
}) async {
  throw UnsupportedError('Downloads are only supported on the web build.');
}
