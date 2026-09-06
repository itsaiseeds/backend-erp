import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/network/api_exception.dart';
import 'package:admin_saiseeds/core/constants/app_strings.dart';

class _StubAdapter implements HttpClientAdapter {
  _StubAdapter(this.statusCode, this.body);

  final int statusCode;
  final Map<String, dynamic>? body;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    return ResponseBody.fromString(
      body == null ? '' : '{"detail":"${body!['detail']}"}',
      statusCode,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ApiClient _clientReturning(int statusCode, {String? detail}) {
  final dio = Dio(
    BaseOptions(
      baseUrl: 'http://stub.local',
      validateStatus: (status) => status != null && status < 500,
    ),
  );
  dio.httpClientAdapter = _StubAdapter(
    statusCode,
    detail == null ? null : {'detail': detail},
  );
  return ApiClient(dio: dio);
}

Future<ApiException> _captureError(ApiClient client) async {
  try {
    await client.post('/anything');
  } on ApiException catch (e) {
    return e;
  }
  fail('expected an ApiException');
}

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://stub.local');
  });

  test('400 surfaces the server detail verbatim', () async {
    final error = await _captureError(
      _clientReturning(400, detail: 'Invalid phone number or TOTP code.'),
    );
    expect(error.statusCode, 400);
    expect(error.message, 'Invalid phone number or TOTP code.');
  });

  test('429 surfaces the server detail verbatim', () async {
    final error = await _captureError(
      _clientReturning(429, detail: 'Request was throttled. Expected in 51s.'),
    );
    expect(error.statusCode, 429);
    expect(error.message, 'Request was throttled. Expected in 51s.');
  });

  test('429 without a body falls back to the rate-limit message', () async {
    final error = await _captureError(_clientReturning(429));
    expect(error.message, AppStrings.ERROR_RATE_LIMITED);
  });

  test('403 without a body falls back to the permission message', () async {
    final error = await _captureError(_clientReturning(403));
    expect(error.message, AppStrings.ERROR_FORBIDDEN);
  });

  test('404 without a body falls back to the not-found message', () async {
    final error = await _captureError(_clientReturning(404));
    expect(error.message, AppStrings.ERROR_NOT_FOUND);
  });

  test('500 falls back to the server-error message', () async {
    final error = await _captureError(_clientReturning(500));
    expect(error.message, AppStrings.ERROR_SERVER);
  });

  test('403 is not treated as an expired session', () {
    const forbidden = ApiProbeResult(statusCode: 403);
    const unauthorized = ApiProbeResult(statusCode: 401);
    expect(forbidden.isUnauthorized, isFalse);
    expect(unauthorized.isUnauthorized, isTrue);
  });
}
