import 'package:web/web.dart' as web;

String? readCookie(String name) {
  final String raw = web.document.cookie;
  if (raw.isEmpty) return null;

  for (final String part in raw.split(';')) {
    final String entry = part.trim();
    final int separator = entry.indexOf('=');
    if (separator <= 0) continue;
    if (entry.substring(0, separator) != name) continue;

    final String value = entry.substring(separator + 1);
    if (value.isEmpty) return null;
    return Uri.decodeComponent(value);
  }
  return null;
}
