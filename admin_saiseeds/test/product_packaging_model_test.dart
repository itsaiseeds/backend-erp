import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/product_packagings/data/models/product_packaging_model.dart';

void main() {
  group('ProductPackagingModel.fromJson', () {
    test('parses the list payload with nested product and string decimals', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-7f3a91c2',
          'product': {'public_id': 'P-4b21ee90', 'name': 'Super Hybrid 101'},
          'packet_weight': '25.000',
          'packets': 5,
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
      expect(packaging.packetWeight, '25.000');
      expect(packaging.packets, 5);
      expect(packaging.packetsLabel, '5');
      expect(packaging.totalWeight, '125.000');
      expect(packaging.sellingPrice, '6000.00');
    });

    test('exposes numeric values parsed from the decimal strings', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-1',
          'product': {'public_id': 'P-1', 'name': 'Priced'},
          'packet_weight': '12.500',
          'packets': 4,
          'total_weight': '50.000',
          'selling_price': '4800.75',
        },
      );

      expect(packaging.packetWeightValue, 12.5);
      expect(packaging.totalWeightValue, 50);
      expect(packaging.sellingPriceValue, 4800.75);
    });

    test('coerces numeric decimals into their string form', () {
      final ProductPackagingModel packaging = ProductPackagingModel.fromJson(
        const {
          'public_id': 'PP-numeric',
          'product': {'public_id': 'P-2', 'name': 'Numeric'},
          'packet_weight': 25.0,
          'packets': 2,
          'total_weight': 50.0,
          'selling_price': 3000.5,
        },
      );

      expect(packaging.packetWeight, '25.0');
      expect(packaging.packetWeightValue, 25);
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
      expect(packaging.packetWeight, '');
      expect(packaging.packetWeightValue, isNull);
      expect(packaging.packets, 0);
      expect(packaging.packetsLabel, '');
      expect(packaging.totalWeight, '');
      expect(packaging.sellingPrice, '');
    });

    test('parses the exact array payload the list endpoint returns', () {
      const List<Map<String, dynamic>> payload = [
        {
          'public_id': 'PP-aaa',
          'product': {'public_id': 'P-aaa', 'name': 'Alpha'},
          'packet_weight': '25.000',
          'packets': 5,
          'total_weight': '125.000',
          'selling_price': '6000.00',
        },
        {
          'public_id': 'PP-bbb',
          'product': {'public_id': 'P-bbb', 'name': 'Beta'},
          'packet_weight': '50.000',
          'packets': 2,
          'total_weight': '100.000',
          'selling_price': '3000.00',
        },
      ];

      final List<ProductPackagingModel> packagings = payload
          .map(ProductPackagingModel.fromJson)
          .toList();

      expect(packagings, hasLength(2));
      expect(packagings.first.productName, 'Alpha');
      expect(packagings.first.packets, 5);
      expect(packagings.last.totalWeightValue, 100);
      expect(packagings.last.sellingPriceValue, 3000);
    });
  });
}
