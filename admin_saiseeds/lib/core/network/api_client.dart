import 'dart:async';

import 'package:dio/dio.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:cookie_jar/cookie_jar.dart';
import 'package:flutter/foundation.dart';
import 'api_config.dart';
import 'api_exception.dart';
import 'cookies/cookie_reader.dart';
import 'cookies/web_cookie_names.dart';
import 'endpoints/auth_endpoints.dart';
import '../constants/app_strings.dart';
import '../services/session_guard.dart';

class ApiClient {
  late final Dio _dio;
  late final CookieJar _cookieJar;

  ApiClient({Dio? dio}) {
    _cookieJar = CookieJar();

    _dio =
        dio ??
        Dio(
          BaseOptions(
            baseUrl: ApiConfig.baseUrl,
            connectTimeout: ApiConfig.timeout,
            receiveTimeout: ApiConfig.timeout,
            sendTimeout: kIsWeb ? null : ApiConfig.timeout,
            headers: ApiConfig.defaultHeaders,
            validateStatus: (status) => status != null && status < 500,
          ),
        );

    if (!kIsWeb) {
      _dio.interceptors.add(CookieManager(_cookieJar));
    }

    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (kIsWeb) {
            options.extra[WebCookieNames.WITH_CREDENTIALS_EXTRA] = true;
          }

          if (_isMutating(options.method)) {
            final String? csrfToken = readCookie(WebCookieNames.CSRF_COOKIE);
            if (csrfToken != null && csrfToken.isNotEmpty) {
              options.headers[WebCookieNames.CSRF_HEADER] = csrfToken;
            }
          }

          return handler.next(options);
        },
        onError: (err, handler) async {
          if (err.response?.statusCode == _unauthorizedStatus &&
              !_isLoginRequest(err.requestOptions.path)) {
            await SessionGuard.endSession();
          }
          return handler.next(err);
        },
      ),
    );
  }

  static const int _unauthorizedStatus = 401;
  static const int _forbiddenStatus = 403;
  static const int _notFoundStatus = 404;
  static const int _rateLimitedStatus = 429;

  static const Set<String> _mutatingMethods = {
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
  };

  static bool _isMutating(String method) =>
      _mutatingMethods.contains(method.toUpperCase());

  static bool _isLoginRequest(String path) =>
      path.endsWith(AuthEndpoints.verifyOtp);

  Future<dynamic> get(
    String endpoint, {
    Map<String, dynamic>? queryParams,
  }) async {
    try {
      final response = await _dio.get(endpoint, queryParameters: queryParams);
      return _processResponse(response);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<ApiProbeResult> probe(String endpoint) async {
    try {
      final response = await _dio.get(endpoint);
      return ApiProbeResult(
        statusCode: response.statusCode ?? 0,
        data: response.data,
      );
    } on DioException catch (e) {
      final int? statusCode = e.response?.statusCode;
      if (statusCode == null) return const ApiProbeResult.unreachable();
      return ApiProbeResult(statusCode: statusCode, data: e.response?.data);
    } catch (_) {
      return const ApiProbeResult.unreachable();
    }
  }

  Future<dynamic> post(String endpoint, {dynamic body}) async {
    try {
      final response = await _dio.post(endpoint, data: body);
      return _processResponse(response);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<dynamic> put(String endpoint, {dynamic body}) async {
    try {
      final response = await _dio.put(endpoint, data: body);
      return _processResponse(response);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<dynamic> delete(String endpoint, {dynamic body}) async {
    try {
      final response = await _dio.delete(endpoint, data: body);
      return _processResponse(response);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<dynamic> patch(String endpoint, {dynamic body}) async {
    try {
      final response = await _dio.patch(endpoint, data: body);
      return _processResponse(response);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  dynamic _processResponse(Response response) {
    final statusCode = response.statusCode;
    if (statusCode != null && statusCode >= 200 && statusCode < 300) {
      return response.data;
    }
    if (statusCode == _unauthorizedStatus &&
        !_isLoginRequest(response.requestOptions.path)) {
      unawaited(SessionGuard.endSession());
    }
    throw ApiException(
      statusCode: statusCode ?? 500,
      message: statusCode == _rateLimitedStatus
          ? AppStrings.ERROR_RATE_LIMITED
          : _extractErrorMessage(response.data, statusCode),
    );
  }

  ApiException _handleDioError(DioException e) {
    final response = e.response;
    if (response != null) {
      final int? statusCode = response.statusCode;
      return ApiException(
        statusCode: statusCode ?? 500,
        message: statusCode == _rateLimitedStatus
            ? AppStrings.ERROR_RATE_LIMITED
            : _extractErrorMessage(response.data, statusCode),
      );
    }

    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiException.unknown(AppStrings.ERROR_TIMEOUT);
      case DioExceptionType.connectionError:
      case DioExceptionType.unknown:
        return ApiException.unknown(AppStrings.ERROR_NETWORK);
      case DioExceptionType.cancel:
        return ApiException.unknown(AppStrings.ERROR_CANCELLED);
      default:
        return ApiException.unknown(AppStrings.SOMETHING_WENT_WRONG);
    }
  }

  String _extractErrorMessage(dynamic data, [int? statusCode]) {
    if (data is Map) {
      final detail = data['detail'];
      if (detail is String && detail.isNotEmpty) return detail;
      final message = data['message'];
      if (message is List && message.isNotEmpty) return message.join('\n');
      if (message is String && message.isNotEmpty) return message;
      final error = data['error'];
      if (error is String && error.isNotEmpty) return error;
    }
    return _fallbackMessageFor(statusCode);
  }

  String _fallbackMessageFor(int? statusCode) {
    switch (statusCode) {
      case _forbiddenStatus:
        return AppStrings.ERROR_FORBIDDEN;
      case _notFoundStatus:
        return AppStrings.ERROR_NOT_FOUND;
      case _rateLimitedStatus:
        return AppStrings.ERROR_RATE_LIMITED;
    }
    if (statusCode != null && statusCode >= 500) {
      return AppStrings.ERROR_SERVER;
    }
    return AppStrings.SOMETHING_WENT_WRONG;
  }
}

class ApiProbeResult {
  final int statusCode;
  final dynamic data;

  const ApiProbeResult({required this.statusCode, this.data});

  const ApiProbeResult.unreachable() : statusCode = 0, data = null;

  bool get isUnreachable => statusCode == 0;

  bool get isSuccess => statusCode >= 200 && statusCode < 300;

  bool get isUnauthorized => statusCode == 401;

  bool get isMissingEndpoint => statusCode == 404;
}
