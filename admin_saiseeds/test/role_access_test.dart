import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:admin_saiseeds/core/constants/user_roles.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/services/session_guard.dart';

Map<String, dynamic> _payloadFor(String role) => {
  'user': {
    'id': 1,
    'name': 'someone',
    'phone_number': '9999999999',
    'role': role,
  },
  'can_create_admin': false,
  'can_create_sales_person': false,
};

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  tearDown(() {
    SessionGuard.prober = null;
    SessionGuard.clearRoleRejection();
  });

  group('UserRoles.canAccessPortal', () {
    test('allows superuser and admin', () {
      expect(UserRoles.canAccessPortal(UserRoles.SUPERUSER), isTrue);
      expect(UserRoles.canAccessPortal(UserRoles.ADMIN), isTrue);
    });

    test('rejects salesperson, plain user, empty and null', () {
      expect(UserRoles.canAccessPortal(UserRoles.SALESPERSON), isFalse);
      expect(UserRoles.canAccessPortal(UserRoles.USER), isFalse);
      expect(UserRoles.canAccessPortal(''), isFalse);
      expect(UserRoles.canAccessPortal(null), isFalse);
    });

    test('is case and whitespace tolerant', () {
      expect(UserRoles.canAccessPortal('  SuperUser '), isTrue);
      expect(UserRoles.canAccessPortal(' ADMIN'), isTrue);
    });
  });

  group('SessionGuard role gate', () {
    test('a superuser session is accepted', () async {
      SharedPreferences.setMockInitialValues({});
      SessionGuard.prober = (_) async => ApiProbeResult(
        statusCode: 200,
        data: _payloadFor(UserRoles.SUPERUSER),
      );

      expect(await SessionGuard.refresh(), isTrue);
      expect(SessionGuard.wasRoleRejected, isFalse);
    });

    test('a salesperson session is rejected and flagged', () async {
      SharedPreferences.setMockInitialValues({});
      SessionGuard.prober = (_) async => ApiProbeResult(
        statusCode: 200,
        data: _payloadFor(UserRoles.SALESPERSON),
      );

      expect(await SessionGuard.refresh(), isFalse);
      expect(SessionGuard.wasRoleRejected, isTrue);
    });

    test('a plain user session is rejected', () async {
      SharedPreferences.setMockInitialValues({});
      SessionGuard.prober = (_) async =>
          ApiProbeResult(statusCode: 200, data: _payloadFor(UserRoles.USER));

      expect(await SessionGuard.refresh(), isFalse);
    });
  });
}
