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

  Uri _uri(String path) {
    // Normalize so both "https://host" and "https://host/" work, avoiding
    // double slashes when concatenating "/api/...".
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    return Uri.parse('$base$path');
  }

  /// Exchange a phone number + authenticator-app TOTP code for a session.
  ///
  /// The server sets the session cookie itself (`Set-Cookie: sessionid`); this
  /// only returns the raw payload `{user, can_create_admin,
  /// can_create_sales_person}`, or throws [ApiException].
  Future<Map<String, dynamic>> verifyOtp({
    required String phoneNumber,
    required String otp,
  }) async {
    final http.Response response;
    try {
      response = await http
          .post(
            _uri('/api/sales-admin/auth/otp/verify'),
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
