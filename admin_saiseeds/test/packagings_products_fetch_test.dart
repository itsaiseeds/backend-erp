import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/services/products_service.dart';
import 'package:admin_saiseeds/features/product_packagings/presentation/views/product_packagings_view.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String _productsBody =
    '[{"public_id":"P-1","name":"SAI-30","crop":"Bajra",'
    '"stage":{"code":"BREEDER","name":"Breeder"},"selling_price":"120.00",'
    '"image_url":"","description_items":[]},'
    '{"public_id":"P-2","name":"SAI-31","crop":"Cotton",'
    '"stage":{"code":"FOUNDATION","name":"Foundation"},'
    '"selling_price":"140.00","image_url":"","description_items":[]}]';

const String _packagingsBody =
    '{"total_count":0,"total_pages":0,"next_page_number":null,'
    '"previous_page_number":null,"results":[],'
    '"available_filters":[],"available_sorts":[]}';

class _CountingAdapter implements HttpClientAdapter {
  final List<String> productRequests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final String path = options.path;
    final bool isProducts =
        path.contains('/products') && !path.contains('packagings');

    if (isProducts) productRequests.add(path);

    return ResponseBody.fromString(
      isProducts ? _productsBody : _packagingsBody,
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ApiClient _clientOf(_CountingAdapter adapter) {
  final dio = Dio(
    BaseOptions(
      baseUrl: 'https://example.test',
      validateStatus: (status) => status != null && status < 500,
    ),
  );
  dio.httpClientAdapter = adapter;
  return ApiClient(dio: dio);
}

Future<void> _openTab(WidgetTester tester, _CountingAdapter adapter) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1600, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Provider<ApiClient>.value(
          value: _clientOf(adapter),
          child: const ProductPackagingsView(),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=https://example.test');
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    ProductsService.instance.reset();
  });

  testWidgets('opening the tab fetches the product list', (tester) async {
    final adapter = _CountingAdapter();

    await _openTab(tester, adapter);

    expect(adapter.productRequests, isNotEmpty);
    expect(ProductsService.instance.products, hasLength(2));
  });

  testWidgets('every product on the list is available, not just a page', (
    tester,
  ) async {
    final adapter = _CountingAdapter();

    await _openTab(tester, adapter);

    final List<String> names = ProductsService.instance.products
        .map((product) => product.name)
        .toList();
    expect(names, containsAll(<String>['SAI-30', 'SAI-31']));
  });

  testWidgets('reopening the tab refetches rather than serving a stale cache', (
    tester,
  ) async {
    final adapter = _CountingAdapter();

    await _openTab(tester, adapter);
    final int afterFirst = adapter.productRequests.length;

    // Leaving the tab and coming back remounts the view.
    await tester.pumpWidget(const MaterialApp(home: Scaffold()));
    await tester.pumpAndSettle();
    await _openTab(tester, adapter);

    // A product added from the Products tab must show up here without a
    // full page reload, so the tab cannot trust the cached list.
    expect(adapter.productRequests.length, greaterThan(afterFirst));
  });

  testWidgets('products are looked up by public id for an existing row', (
    tester,
  ) async {
    final adapter = _CountingAdapter();

    await _openTab(tester, adapter);

    expect(ProductsService.instance.productByPublicId('P-2')?.name, 'SAI-31');
    expect(ProductsService.instance.productByPublicId('P-9'), isNull);
  });
}
