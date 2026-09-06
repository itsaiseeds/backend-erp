import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/sales_people/data/models/sales_person_model.dart';

void main() {
  group('SalesPersonModel.fromJson', () {
    test('parses the full payload including nested city and totp', () {
      final SalesPersonModel person = SalesPersonModel.fromJson(const {
        'id': 21,
        'name': 'Field Rep',
        'email': 'rep@example.com',
        'phone_number': '9123456780',
        'role': 'sales_person',
        'created_by': {'id': 12, 'name': 'Harsh Mori'},
        'created_at': '2026-08-20T08:00:00Z',
        'city': {'id': 105, 'name': 'Rajkot'},
        'totp': {
          'provisioning_uri':
              'otpauth://totp/Saiseeds:rep?secret=XYZ789&issuer=Saiseeds',
        },
      });

      expect(person.id, '21');
      expect(person.name, 'Field Rep');
      expect(person.email, 'rep@example.com');
      expect(person.phoneNumber, '9123456780');
      expect(person.role, 'sales_person');
      expect(person.createdBy!.name, 'Harsh Mori');
      expect(person.createdByName, 'Harsh Mori');
      expect(person.city, isNotNull);
      expect(person.city!.id, 105);
      expect(person.cityId, 105);
      expect(person.cityName, 'Rajkot');
      expect(
        person.provisioningUri,
        'otpauth://totp/Saiseeds:rep?secret=XYZ789&issuer=Saiseeds',
      );
    });

    test('tolerates a missing city and totp', () {
      final SalesPersonModel person = SalesPersonModel.fromJson(const {
        'id': 22,
        'name': 'Cityless Rep',
        'phone_number': '9000000001',
        'city': null,
        'totp': null,
      });

      expect(person.city, isNull);
      expect(person.cityId, isNull);
      expect(person.cityName, '');
      expect(person.provisioningUri, '');
    });
  });
}
