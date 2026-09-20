import 'dart:convert';
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

import 'phone_number_formatter.dart';

const String _pngMimeType = 'image/png';

void openWhatsApp({required String phoneNumber, required String message}) {
  final String dialable = PhoneNumberFormatter.toWhatsAppNumber(phoneNumber);
  if (dialable.isEmpty) return;

  final String url =
      'https://wa.me/$dialable?text=${Uri.encodeComponent(message)}';
  web.window.open(url, '_blank');
}

void downloadPngBytes({required String fileName, required Uint8List bytes}) {
  if (bytes.isEmpty) return;

  final String href = 'data:$_pngMimeType;base64,${base64Encode(bytes)}';
  final web.HTMLAnchorElement anchor =
      web.document.createElement('a') as web.HTMLAnchorElement
        ..href = href
        ..download = fileName;

  web.document.body?.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

Future<bool> shareQrImage({
  required String fileName,
  required Uint8List bytes,
  required String title,
  required String message,
}) async {
  if (bytes.isEmpty) return false;

  try {
    final web.Blob blob = web.Blob(
      <JSAny>[bytes.toJS].toJS,
      web.BlobPropertyBag(type: _pngMimeType),
    );
    final web.File file = web.File(
      <JSAny>[blob].toJS,
      fileName,
      web.FilePropertyBag(type: _pngMimeType),
    );
    final web.ShareData data = web.ShareData(
      files: <web.File>[file].toJS,
      text: message,
      title: title,
    );

    if (!web.window.navigator.canShare(data)) return false;

    await web.window.navigator.share(data).toDart;
    return true;
  } catch (_) {
    return false;
  }
}
