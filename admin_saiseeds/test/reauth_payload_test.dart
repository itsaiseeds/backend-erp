import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/services/session_guard.dart';
import 'package:admin_saiseeds/core/services/storage_service.dart';

const Map<String, dynamic> _reauthResponse = {
  'user': {
    'id': 1,
    'name': 'admin',
    'phone_number': '9999999999',
    'role': 'superuser',
  },
  'can_create_admin': true,
  'can_create_sales_person': true,
};

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  tearDown(() => SessionGuard.prober = null);

  test('200 payload hydrates the cached profile', () async {
    SharedPreferences.setMockInitialValues({});
    SessionGuard.prober = (_) async =>
        const ApiProbeResult(statusCode: 200, data: _reauthResponse);

    final bool valid = await SessionGuard.refresh();

    expect(valid, isTrue);
    expect(await StorageService.getUserId(), 1);
    expect(await StorageService.getUserName(), 'admin');
    expect(await StorageService.getUserPhoneNumber(), '9999999999');
    expect(await StorageService.getUserRole(), 'superuser');
    expect(await StorageService.getCanCreateAdmin(), isTrue);
    expect(await StorageService.getCanCreateSalesPerson(), isTrue);
  });

  test('401 clears the cached profile and invalidates the session', () async {
    SharedPreferences.setMockInitialValues({
      'user_name': 'admin',
      'user_role': 'superuser',
      'user_phone_number': '9999999999',
    });
    SessionGuard.prober = (_) async => const ApiProbeResult(statusCode: 401);

    final bool valid = await SessionGuard.refresh();

    expect(valid, isFalse);
    expect(await StorageService.hasCachedProfile(), isFalse);
  });

  test('demoted permissions overwrite the cached values', () async {
    SharedPreferences.setMockInitialValues({});
    SessionGuard.prober = (_) async => const ApiProbeResult(
      statusCode: 200,
      data: {
        'user': {
          'id': 2,
          'name': 'demoted',
          'phone_number': '8888888888',
          'role': 'admin',
        },
        'can_create_admin': false,
        'can_create_sales_person': true,
      },
    );

    await SessionGuard.refresh();

    expect(await StorageService.getCanCreateAdmin(), isFalse);
    expect(await StorageService.getCanCreateSalesPerson(), isTrue);
  });
}
