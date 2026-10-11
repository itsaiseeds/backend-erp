import 'package:dio/dio.dart' show Headers;

class ApiException implements Exception {
  final String message;
  final int? statusCode;

  /// Only ever set when the caller asked for them (see
  /// `ApiClient.getWithHeaders`) -- `null` for every other call site.
  final Headers? headers;

  const ApiException({required this.message, this.statusCode, this.headers});

  factory ApiException.unknown(String message) =>
      ApiException(message: message);

  /// The seconds a 429 asks the caller to wait, from its `Retry-After`
  /// header -- null when absent or not a plain integer.
  int? get retryAfterSeconds {
    final String? raw = headers?.value('retry-after');
    if (raw == null) return null;
    return int.tryParse(raw.trim());
  }

  @override
  String toString() =>
      'ApiException(statusCode: $statusCode, message: $message)';
}
