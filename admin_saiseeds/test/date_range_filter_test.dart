import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/widgets/inputs/date_range_field.dart';
import 'package:admin_saiseeds/features/clients/data/models/client_filter_model.dart';

void main() {
  group('date range encoding', () {
    test('round-trips a range through the wire format', () {
      final value = DateRangeValue(
        start: DateTime(2026, 1, 15),
        end: DateTime(2026, 3, 20),
      );

      expect(value.wireValue, '2026-01-15|2026-03-20');

      final parsed = DateRangeValue.parse(value.wireValue);
      expect(parsed.start, DateTime(2026, 1, 15));
      expect(parsed.end, DateTime(2026, 3, 20));
    });

    test('renders a human readable label', () {
      final value = DateRangeValue(
        start: DateTime(2026, 1, 15),
        end: DateTime(2026, 3, 20),
      );

      expect(value.displayValue, '15 Jan 2026 → 20 Mar 2026');
    });

    test('an empty string parses to an empty range', () {
      expect(DateRangeValue.parse('').isEmpty, isTrue);
    });

    test('garbage does not throw', () {
      expect(DateRangeValue.parse('not-a-date|also-bad').isEmpty, isTrue);
    });

    test('range splits into the backend param names', () {
      final filter = ClientFilterModel.fromJson({
        'filter': 'created',
        'label': 'Created',
        'kind': 'datetime_range',
        'params': ['created_gte', 'created_lte'],
      });

      final parts = '2026-01-15|2026-03-20'.split(DateRangeValue.SEPARATOR);

      expect(filter.lowerBoundParam, 'created_gte');
      expect(filter.upperBoundParam, 'created_lte');
      expect(parts.first, '2026-01-15');
      expect(parts[1], '2026-03-20');
    });
  });
}
