import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/product_packagings/presentation/widgets/selling_price_autofill.dart';

void main() {
  group('SellingPriceAutofill', () {
    test('computes bags times the product selling price', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '5'),
        '6000.00',
      );
    });

    test('recomputes when the bag count changes', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '5'),
        '6000.00',
      );
      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '2'),
        '2400.00',
      );
    });

    test('recomputes when the product changes', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '3'),
        '3600.00',
      );
      expect(
        autofill.nextValue(productSellingPrice: 900.5, bags: '3'),
        '2701.50',
      );
    });

    test('stops recomputing once the field is manually edited', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      final String? computed = autofill.nextValue(
        productSellingPrice: 1200,
        bags: '5',
      );
      expect(computed, '6000.00');

      autofill.registerFieldChange('7777.00');
      expect(autofill.isManuallyEdited, isTrue);

      expect(autofill.nextValue(productSellingPrice: 1200, bags: '9'), isNull);
      expect(autofill.nextValue(productSellingPrice: 50, bags: '2'), isNull);
    });

    test('an echo of its own autofilled value is not a manual edit', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      final String? computed = autofill.nextValue(
        productSellingPrice: 1200,
        bags: '5',
      );
      autofill.registerFieldChange(computed!);

      expect(autofill.isManuallyEdited, isFalse);
      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '6'),
        '7200.00',
      );
    });

    test('an existing value on an edit form suppresses autofill', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();
      autofill.adoptExistingValue('6000.00');

      expect(autofill.isManuallyEdited, isTrue);
      expect(autofill.nextValue(productSellingPrice: 1200, bags: '5'), isNull);
    });

    test('an empty existing value leaves autofill armed', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();
      autofill.adoptExistingValue('   ');

      expect(autofill.isManuallyEdited, isFalse);
      expect(
        autofill.nextValue(productSellingPrice: 1200, bags: '5'),
        '6000.00',
      );
    });

    test('yields nothing without a product or a usable bag count', () {
      final SellingPriceAutofill autofill = SellingPriceAutofill();

      expect(autofill.nextValue(productSellingPrice: null, bags: '5'), isNull);
      expect(autofill.nextValue(productSellingPrice: 1200, bags: ''), isNull);
      expect(autofill.nextValue(productSellingPrice: 1200, bags: '0'), isNull);
      expect(autofill.nextValue(productSellingPrice: 1200, bags: 'x'), isNull);
      expect(autofill.isManuallyEdited, isFalse);
    });
  });
}
