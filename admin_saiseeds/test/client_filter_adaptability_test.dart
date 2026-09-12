import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_filter_model.dart';

void main() {
  group('backend-driven filters', () {
    test('uses the backend label for a select value', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'city_id',
        'kind': 'select',
        'description': 'City id(s).',
        'options': [
          {'value': 2, 'label': 'Ahmedabad'},
          {'value': 1, 'label': 'Surat'},
        ],
      });

      expect(filter.labelForValue('1'), 'Surat');
      expect(filter.labelForValue('2'), 'Ahmedabad');
    });

    test('falls back to the raw value when the option is gone', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'city_id',
        'kind': 'select',
        'options': [
          {'value': 1, 'label': 'Surat'},
        ],
      });

      expect(filter.labelForValue('99'), '99');
    });

    test('a brand new filter the app has never seen still parses', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'region_id',
        'kind': 'select',
        'description': 'Newly added by backend.',
        'options': [
          {'value': 7, 'label': 'West'},
        ],
      });

      expect(filter.key, 'region_id');
      expect(filter.isSelect, isTrue);
      expect(filter.labelForValue('7'), 'West');
    });

    test('an unknown kind degrades instead of throwing', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'weird',
        'kind': 'colour_picker',
      });

      expect(filter.kind, ClientFilterKind.unsupported);
    });

    test('datetime range reads its params from the backend', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'created',
        'kind': 'datetime_range',
        'params': ['created_gte', 'created_lte'],
      });

      expect(filter.lowerBoundParam, 'created_gte');
      expect(filter.upperBoundParam, 'created_lte');
    });

    test('datetime range without params falls back to a convention', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'updated',
        'kind': 'datetime_range',
      });

      expect(filter.lowerBoundParam, 'updated_gte');
      expect(filter.upperBoundParam, 'updated_lte');
    });

    test('uses the backend label for the filter name', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'city_id',
        'label': 'City',
        'kind': 'select',
      });

      expect(filter.displayLabel, 'City');
    });

    test('falls back to the raw key when no label is sent', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'city_id',
        'kind': 'select',
      });

      expect(filter.displayLabel, 'city_id');
    });

    test('uses the backend label for a sort', () {
      final sort = ClientSortModel.fromJson({
        'sort': 'company_name',
        'label': 'Company Name',
      });

      expect(sort.displayLabel, 'Company Name');
    });

    test('sort falls back to the raw key when no label is sent', () {
      final sort = ClientSortModel.fromJson({'sort': 'created_at'});

      expect(sort.displayLabel, 'created_at');
    });

    test('sorts parse from the backend list', () {
      final sort = ClientSortModel.fromJson({
        'sort': 'company_name',
        'description': 'Company name, A->Z.',
      });

      expect(sort.key, 'company_name');
      expect(sort.description, 'Company name, A->Z.');
    });
  });
}
