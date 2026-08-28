import 'dart:convert';

import 'package:http/http.dart' as http;

/// Thin wrapper around the sales admin backend.
///
/// The backend base URL defaults to a local dev server and can be overridden
/// at build time:
///   flutter run --dart-define=API_BASE_URL=https://api.example.com
class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = baseUrl ??
            const String.fromEnvironment(
              'API_BASE_URL',
              defaultValue: 'http://localhost:8000',
            );

  final String baseUrl;

  Uri _uri(String path) => Uri.parse('$baseUrl$path');

  /// Exchange a phone number + authenticator-app TOTP code for credentials.
  ///
  /// Returns the raw payload `{token, user}` or throws [ApiException].
  Future<Map<String, dynamic>> verifyOtp({
    required String phoneNumber,
    required String otp,
  }) async {
    final http.Response response;
    try {
      response = await http
          .post(
            _uri('/api/sales_admin/auth/otp/verify'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'phone_number': phoneNumber,
              'otp': otp,
            }),
          )
          .timeout(const Duration(seconds: 15));
    } catch (e) {
      throw ApiException('Could not reach the server. Is it running?');
    }

    final decoded = _decode(response);
    if (response.statusCode != 200) {
      throw ApiException(
        decoded is Map<String, dynamic> && decoded['detail'] != null
            ? decoded['detail'] as String
            : 'Sign in failed (HTTP ${response.statusCode}).',
      );
    }
    return decoded as Map<String, dynamic>;
  }

  dynamic _decode(http.Response response) {
    try {
      return jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      return null;
    }
  }
}

class ApiException implements Exception {
  ApiException(this.message);
  final String message;

  @override
  String toString() => message;
}
