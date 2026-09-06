import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/product_packagings/data/models/product_packaging_model.dart';

void main() {
  group('ProductPackagingModel.fromJson', () {
    test('parses the list payload with nested product and string decimals', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-7f3a91c2',
          'product': {'public_id': 'P-4b21ee90', 'name': 'Super Hybrid 101'},
          'packing_bag_weight': '25.000',
          'packing_bags': 5,
          'total_weight': '125.000',
          'selling_price': '6000.00',
        },
      );

      expect(packaging.publicId, 'PP-7f3a91c2');
      expect(packaging.product, isNotNull);
      expect(packaging.product!.publicId, 'P-4b21ee90');
      expect(packaging.product!.name, 'Super Hybrid 101');
      expect(packaging.productPublicId, 'P-4b21ee90');
      expect(packaging.productName, 'Super Hybrid 101');
      expect(packaging.packingBagWeight, '25.000');
      expect(packaging.packingBags, 5);
      expect(packaging.packingBagsLabel, '5');
      expect(packaging.totalWeight, '125.000');
      expect(packaging.sellingPrice, '6000.00');
    });

    test('exposes numeric values parsed from the decimal strings', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-1',
          'product': {'public_id': 'P-1', 'name': 'Priced'},
          'packing_bag_weight': '12.500',
          'packing_bags': 4,
          'total_weight': '50.000',
          'selling_price': '4800.75',
        },
      );

      expect(packaging.packingBagWeightValue, 12.5);
      expect(packaging.totalWeightValue, 50);
      expect(packaging.sellingPriceValue, 4800.75);
    });

    test('coerces numeric decimals into their string form', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-numeric',
          'product': {'public_id': 'P-2', 'name': 'Numeric'},
          'packing_bag_weight': 25.0,
          'packing_bags': 2,
          'total_weight': 50.0,
          'selling_price': 3000.5,
        },
      );

      expect(packaging.packingBagWeight, '25.0');
      expect(packaging.packingBagWeightValue, 25);
      expect(packaging.totalWeight, '50.0');
      expect(packaging.sellingPrice, '3000.5');
      expect(packaging.sellingPriceValue, 3000.5);
    });

    test('tolerates a missing product and absent decimal keys', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {'public_id': 'PP-orphan', 'product': null},
      );

      expect(packaging.publicId, 'PP-orphan');
      expect(packaging.product, isNull);
      expect(packaging.productName, '');
      expect(packaging.productPublicId, '');
      expect(packaging.packingBagWeight, '');
      expect(packaging.packingBagWeightValue, isNull);
      expect(packaging.packingBags, 0);
      expect(packaging.packingBagsLabel, '');
      expect(packaging.totalWeight, '');
      expect(packaging.sellingPrice, '');
    });

    test('parses the exact array payload the list endpoint returns', () {
      const List<Map<String, dynamic>> payload = [
        {
          'public_id': 'PP-aaa',
          'product': {'public_id': 'P-aaa', 'name': 'Alpha'},
          'packing_bag_weight': '25.000',
          'packing_bags': 5,
          'total_weight': '125.000',
          'selling_price': '6000.00',
        },
        {
          'public_id': 'PP-bbb',
          'product': {'public_id': 'P-bbb', 'name': 'Beta'},
          'packing_bag_weight': '50.000',
          'packing_bags': 2,
          'total_weight': '100.000',
          'selling_price': '3000.00',
        },
      ];

      final List<ProductPackagingModel> packagings = payload
          .map(ProductPackagingModel.fromJson)
          .toList();

      expect(packagings, hasLength(2));
      expect(packagings.first.productName, 'Alpha');
      expect(packagings.first.packingBags, 5);
      expect(packagings.last.totalWeightValue, 100);
      expect(packagings.last.sellingPriceValue, 3000);
    });
  });
}
