import 'package:flutter/widgets.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/core/config/app_config_keys.dart';
import 'package:admin_saiseeds/features/products/data/models/product_model.dart';

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await dotenv.load(fileName: AppConfigKeys.ENV_FILE_DEV);
  });

  test('detail dialog requests an absolute media URL', () {
    final p = ProductModel.fromJson({
      'image_url': '/media/products/16ae50b2731b4a30ab3b086d64a63c9e.jpg',
    });

    debugPrint('image URL -> ${p.imageDisplayUrl}');
    expect(p.imageDisplayUrl,
        'http://localhost:8000/media/products/16ae50b2731b4a30ab3b086d64a63c9e.jpg');
  });
}
