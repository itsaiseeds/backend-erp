class ApiException implements Exception {
  final String message;
  final int? statusCode;

  const ApiException({required this.message, this.statusCode});

  factory ApiException.unknown(String message) =>
      ApiException(message: message);

  @override
  String toString() => 'ApiException(statusCode: $statusCode, message: $message)';
}
