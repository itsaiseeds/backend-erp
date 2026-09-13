import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';

void main() {
  test('parses the updated GET response shape', () {
    final product = ProductModel.fromJson({
      'public_id': 'P-1',
      'name': 'Hybrid Cotton',
      'crop': {'id': 3, 'name': 'Cotton'},
      'stage': {'id': 2, 'code': 'FOUNDATION', 'name': 'Foundation'},
      'selling_price': '-5',
      'image_url': 'https://cdn/img.png',
      'description_items': ['High yield', 'Drought tolerant'],
    });

    expect(product.publicId, 'P-1');
    expect(product.cropName, 'Cotton');
    expect(product.stageId, 2);
    expect(product.stageName, 'Foundation');
    expect(product.sellingPrice, '-5');
    expect(product.imageUrl, 'https://cdn/img.png');
    expect(product.descriptionItems, ['High yield', 'Drought tolerant']);
  });

  test('tolerates a missing stage, image and description', () {
    final product = ProductModel.fromJson({
      'public_id': 'P-2',
      'name': 'Plain',
      'selling_price': 120,
    });

    expect(product.stage, isNull);
    expect(product.stageName, '');
    expect(product.imageUrl, '');
    expect(product.descriptionItems, isEmpty);
    expect(product.sellingPrice, '120');
  });

  test('drops blank description points', () {
    final product = ProductModel.fromJson({
      'public_id': 'P-3',
      'name': 'X',
      'description_items': ['  ', 'Kept', ''],
    });

    expect(product.descriptionItems, ['Kept']);
  });

  test('resolves a bare numeric stage id', () {
    final product = ProductModel.fromJson({
      'public_id': 'P-4',
      'name': 'X',
      'stage': 4,
    });

    expect(product.stageId, 4);
    expect(product.stageName, 'Certificate');
  });
}
