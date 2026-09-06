import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/admins/data/models/admin_model.dart';

void main() {
  group('AdminModel.fromJson', () {
    test('parses the full admin payload including created_by and totp', () {
      final AdminModel admin = AdminModel.fromJson(const {
        'id': 12,
        'name': 'Harsh Mori',
        'email': 'harsh@example.com',
        'phone_number': '9876543210',
        'role': 'admin',
        'created_by': {'id': 3, 'name': 'Root Admin'},
        'created_at': '2026-09-01T10:15:30Z',
        'can_update_stock_count': true,
        'totp': {
          'provisioning_uri':
              'otpauth://totp/Saiseeds:harsh?secret=ABC123&issuer=Saiseeds',
        },
      });

      expect(admin.id, '12');
      expect(admin.name, 'Harsh Mori');
      expect(admin.email, 'harsh@example.com');
      expect(admin.phoneNumber, '9876543210');
      expect(admin.role, 'admin');
      expect(admin.canUpdateStockCount, isTrue);
      expect(admin.createdAt, '2026-09-01T10:15:30Z');
      expect(admin.createdBy, isNotNull);
      expect(admin.createdBy!.id, 3);
      expect(admin.createdBy!.name, 'Root Admin');
      expect(admin.createdByName, 'Root Admin');
      expect(
        admin.provisioningUri,
        'otpauth://totp/Saiseeds:harsh?secret=ABC123&issuer=Saiseeds',
      );
    });

    test('tolerates a null email and missing nested objects', () {
      final AdminModel admin = AdminModel.fromJson(const {
        'id': 7,
        'name': 'No Email Admin',
        'email': null,
        'phone_number': '9000000000',
        'role': 'admin',
        'created_by': null,
        'created_at': null,
        'can_update_stock_count': false,
        'totp': null,
      });

      expect(admin.id, '7');
      expect(admin.email, '');
      expect(admin.createdBy, isNull);
      expect(admin.createdByName, '');
      expect(admin.provisioningUri, '');
      expect(admin.canUpdateStockCount, isFalse);
    });

    test('coerces a string id and defaults absent keys', () {
      final AdminModel admin = AdminModel.fromJson(const {
        'id': '44',
        'name': 'Partial',
      });

      expect(admin.id, '44');
      expect(admin.phoneNumber, '');
      expect(admin.role, '');
      expect(admin.canUpdateStockCount, isFalse);
    });
  });
}
