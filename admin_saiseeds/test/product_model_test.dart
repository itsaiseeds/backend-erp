import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';

void main() {
  group('ProductModel.fromJson', () {
    test('parses the list payload with nested crop and string prices', () {
      final ProductModel product = ProductModel.fromJson(const {
        'public_id': 'b3f1c2d4-5a6b-7c8d-9e0f-112233445566',
        'name': 'Super Hybrid 101',
        'crop': {'id': 4, 'name': 'Cotton'},
        'buying_price': '1200.00',
        'selling_price': '1500.50',
        'margin_per_bag': '300.50',
      });

      expect(product.publicId, 'b3f1c2d4-5a6b-7c8d-9e0f-112233445566');
      expect(product.name, 'Super Hybrid 101');
      expect(product.crop, isNotNull);
      expect(product.crop!.id, 4);
      expect(product.crop!.name, 'Cotton');
      expect(product.cropId, 4);
      expect(product.cropName, 'Cotton');
      expect(product.buyingPrice, '1200.00');
      expect(product.sellingPrice, '1500.50');
      expect(product.marginPerBag, '300.50');
    });

    test('exposes numeric values parsed from the price strings', () {
      final ProductModel product = ProductModel.fromJson(const {
        'public_id': 'abc',
        'name': 'Priced',
        'crop': {'id': 1, 'name': 'Wheat'},
        'buying_price': '900.25',
        'selling_price': '1000.75',
        'margin_per_bag': '100.50',
      });

      expect(product.buyingPriceValue, 900.25);
      expect(product.sellingPriceValue, 1000.75);
      expect(product.marginPerBagValue, 100.50);
    });

    test('tolerates a missing crop and absent price keys', () {
      final ProductModel product = ProductModel.fromJson(const {
        'public_id': 'no-crop',
        'name': 'Orphan',
        'crop': null,
      });

      expect(product.publicId, 'no-crop');
      expect(product.crop, isNull);
      expect(product.cropId, isNull);
      expect(product.cropName, '');
      expect(product.buyingPrice, '');
      expect(product.buyingPriceValue, isNull);
      expect(product.marginPerBag, '');
    });

    test('coerces a numeric price into its string form', () {
      final ProductModel product = ProductModel.fromJson(const {
        'public_id': 'numeric',
        'name': 'Numeric Price',
        'crop': {'id': '9', 'name': 'Maize'},
        'buying_price': 1200,
        'selling_price': 1500.5,
      });

      expect(product.crop!.id, 9);
      expect(product.buyingPrice, '1200');
      expect(product.sellingPrice, '1500.5');
      expect(product.buyingPriceValue, 1200);
    });

    test('parses an array of products', () {
      const List<Map<String, dynamic>> payload = [
        {
          'public_id': 'p1',
          'name': 'Alpha',
          'crop': {'id': 1, 'name': 'Cotton'},
          'buying_price': '100.00',
          'selling_price': '150.00',
          'margin_per_bag': '50.00',
        },
        {
          'public_id': 'p2',
          'name': 'Beta',
          'crop': {'id': 2, 'name': 'Wheat'},
          'buying_price': '200.00',
          'selling_price': '260.00',
          'margin_per_bag': '60.00',
        },
      ];

      final List<ProductModel> products = payload
          .map(ProductModel.fromJson)
          .toList();

      expect(products, hasLength(2));
      expect(products.first.cropName, 'Cotton');
      expect(products.last.marginPerBagValue, 60);
    });
  });
}
