import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/product_packagings/presentation/widgets/selling_price_autofill.dart';

void main() {
  group('SellingPriceAutofill', () {
    test('multiplies the per-kg rate by weight and packet count', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      // 120/kg x 2.5 kg x 4 packets = 1200
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2.5',
          packets: '4',
        ),
        '1200.00',
      );
    });

    test('a 25 kg packet is not priced as if it were 1 kg', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      // The old rule (rate x packets) gave 200.00 here - off by 25x.
      expect(
        autofill.nextValue(
          productSellingPrice: 100,
          packetWeight: '25',
          packets: '2',
        ),
        '5000.00',
      );
    });

    test('a sub-kilo packet is not over-priced', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      // 200/kg x 0.5 kg x 3 packets = 300, where the old rule gave 600.
      expect(
        autofill.nextValue(
          productSellingPrice: 200,
          packetWeight: '0.5',
          packets: '3',
        ),
        '300.00',
      );
    });

    test('recomputes when the packet weight changes', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '1',
          packets: '10',
        ),
        '1200.00',
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '1.5',
          packets: '10',
        ),
        '1800.00',
      );
    });

    test('recomputes when the packet count changes', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '5',
        ),
        '1200.00',
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '2',
        ),
        '480.00',
      );
    });

    test('recomputes when the product changes', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '3',
        ),
        '720.00',
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 90.5,
          packetWeight: '2',
          packets: '3',
        ),
        '543.00',
      );
    });

    test('matches the live packaging response', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      // PP-5SVE39LY2XEI: 1.5 kg x 20 packets at the SAI-3353 rate of 250/kg.
      expect(
        autofill.nextValue(
          productSellingPrice: 250,
          packetWeight: '1.5',
          packets: '20',
        ),
        '7500.00',
      );
    });

    test('stops autofilling once the field is edited by hand', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '5',
        ),
        '1200.00',
      );

      autofill.markManuallyEdited();

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '3',
          packets: '5',
        ),
        isNull,
      );
    });

    test('an existing value counts as a manual edit', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      autofill.adoptExistingValue('999.00');

      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '5',
        ),
        isNull,
      );
    });

    test('a field change that is not the autofilled value is a manual edit', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      final String? computed = autofill.nextValue(
        productSellingPrice: 120,
        packetWeight: '2',
        packets: '5',
      );
      expect(computed, '1200.00');

      // Echoing back the autofilled value must not count as an edit.
      autofill.registerFieldChange(computed!);
      expect(autofill.isManuallyEdited, isFalse);

      autofill.registerFieldChange('50');
      expect(autofill.isManuallyEdited, isTrue);
    });

    test('returns null for missing or non-positive inputs', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(
          productSellingPrice: null,
          packetWeight: '2',
          packets: '5',
        ),
        isNull,
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '',
          packets: '5',
        ),
        isNull,
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '0',
          packets: '5',
        ),
        isNull,
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: '2',
          packets: '0',
        ),
        isNull,
      );
      expect(
        autofill.nextValue(
          productSellingPrice: 120,
          packetWeight: 'x',
          packets: '5',
        ),
        isNull,
      );
    });
  });
}
