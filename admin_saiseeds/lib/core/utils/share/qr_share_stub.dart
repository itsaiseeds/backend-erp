import 'dart:typed_data';

void openWhatsApp({required String phoneNumber, required String message}) {}

void downloadPngBytes({required String fileName, required Uint8List bytes}) {}

Future<bool> shareQrImage({
  required String fileName,
  required Uint8List bytes,
  required String title,
  required String message,
}) async => false;
