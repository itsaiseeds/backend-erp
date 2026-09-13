import 'package:flutter/widgets.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/config/app_config_keys.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await dotenv.load(fileName: AppConfigKeys.ENV_FILE_PROD);
  });

  test('parses the live response verbatim', () {
    final p = ProductModel.fromJson({
      'public_id': 'P-6SLCGZB8IPTA',
      'name': 'Product A',
      'crop': {'id': 2, 'name': 'Bajari'},
      'stage': {'id': 1, 'code': 'BREEDER', 'name': 'Breeder'},
      'selling_price': 30.0,
      'image_url': '/media/products/16ae50b2731b4a30ab3b086d64a63c9e.jpg',
      'description_items': ['This is test A', 'This is test B'],
    });

    expect(p.name, 'Product A');
    expect(p.cropName, 'Bajari');
    expect(p.stageName, 'Breeder');
    expect(p.sellingPrice, '30');
    expect(p.sellingPriceValue, 30.0);
    expect(p.descriptionItems.length, 2);
    expect(p.imageUrl, '/media/products/16ae50b2731b4a30ab3b086d64a63c9e.jpg');
  });

  test('keeps real decimals but trims a bare .0', () {
    expect(
      ProductModel.fromJson({'selling_price': 30.0}).sellingPrice,
      '30',
    );
    expect(
      ProductModel.fromJson({'selling_price': 30.5}).sellingPrice,
      '30.5',
    );
    expect(
      ProductModel.fromJson({'selling_price': '250'}).sellingPrice,
      '250',
    );
    expect(ProductModel.fromJson({}).sellingPrice, '');
  });

  test('resolves a relative media path against the API host', () {
    final p = ProductModel.fromJson({
      'image_url': '/media/products/abc.jpg',
    });
    expect(p.imageUrl, '/media/products/abc.jpg');
    expect(p.imageDisplayUrl.endsWith('/media/products/abc.jpg'), isTrue);

    final absolute = ProductModel.fromJson({
      'image_url': 'https://cdn.example.com/x.jpg',
    });
    expect(absolute.imageDisplayUrl, 'https://cdn.example.com/x.jpg');

    expect(ProductModel.fromJson({'image_url': ''}).imageDisplayUrl, '');
  });

  test('handles empty image and description', () {
    final p = ProductModel.fromJson({
      'public_id': 'P-I34V7RI1JPUH',
      'name': 'SAI-33',
      'crop': {'id': 1, 'name': 'Castor'},
      'stage': {'id': 1, 'code': 'BREEDER', 'name': 'Breeder'},
      'selling_price': 120.0,
      'image_url': '',
      'description_items': [],
    });

    expect(p.imageUrl, '');
    expect(p.descriptionItems, isEmpty);
    expect(p.sellingPriceValue, 120.0);
  });
}
