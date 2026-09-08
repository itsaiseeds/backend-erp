import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/core/services/crops_service.dart';
import 'package:admin_saiseeds/core/services/session_guard.dart';
import 'package:admin_saiseeds/core/theme/app_theme.dart';
import 'package:admin_saiseeds/core/widgets/tables/app_pagination.dart';
import 'package:admin_saiseeds/features/dashboard/presentation/widgets/dashboard_content_switcher.dart';
import 'package:admin_saiseeds/core/constants/tab_ids.dart';
import 'package:admin_saiseeds/features/products/presentation/views/products_view.dart';
import 'package:admin_saiseeds/features/products/presentation/widgets/products_table.dart';

class _ProductsStubAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    const String products =
        '[{"public_id":"p1","name":"Super Hybrid 101",'
        '"crop":{"id":1,"name":"Cotton"},"buying_price":"1200.00",'
        '"selling_price":"1500.50","margin_per_packet":"300.50"},'
        '{"public_id":"p2","name":"Golden Wheat Select",'
        '"crop":{"id":2,"name":"Wheat"},"buying_price":"900.00",'
        '"selling_price":"1100.00","margin_per_packet":"200.00"}]';
    const String crops = '[{"id":1,"name":"Cotton"},{"id":2,"name":"Wheat"}]';

    return ResponseBody.fromString(
      options.path.contains('crops') ? crops : products,
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ApiClient _stubClient() {
  final Dio dio = Dio(
    BaseOptions(
      baseUrl: 'http://stub.local',
      validateStatus: (status) => status != null && status < 500,
    ),
  );
  dio.httpClientAdapter = _ProductsStubAdapter();
  return ApiClient(dio: dio);
}

Widget _harness() {
  return RepositoryProvider<ApiClient>.value(
    value: _stubClient(),
    child: MaterialApp(
      theme: AppTheme.light,
      home: Scaffold(
        body: DashboardContentSwitcher.screenFor(TabIds.PRODUCTS),
      ),
    ),
  );
}

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://stub.local');
    SharedPreferences.setMockInitialValues({
      'user_name': 'admin',
      'user_role': 'superuser',
      'user_phone_number': '9999999999',
      'can_create_admin': true,
      'can_create_sales_person': true,
    });
    SessionGuard.prober = (_) async => const ApiProbeResult(
      statusCode: 200,
      data: {
        'user': {
          'id': 1,
          'name': 'admin',
          'phone_number': '9999999999',
          'role': 'superuser',
        },
        'can_create_admin': true,
        'can_create_sales_person': true,
      },
    );
  });

  tearDownAll(() => SessionGuard.prober = null);

  setUp(() => CropsService.instance.reset());
  tearDown(() => CropsService.instance.reset());

  testWidgets('products renders without overflow across widths', (
    tester,
  ) async {
    for (final double width in <double>[1600, 1440, 1280, 1024, 900, 768]) {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = Size(width, 1000);
      addTearDown(tester.view.reset);

      await tester.pumpWidget(_harness());
      await tester.pumpAndSettle();

      expect(
        find.byType(ProductsView),
        findsOneWidget,
        reason: 'products view missing at $width',
      );
      expect(
        find.byType(ProductsTable),
        findsOneWidget,
        reason: 'products table missing at $width',
      );
      expect(
        find.text('Super Hybrid 101'),
        findsOneWidget,
        reason: 'product row missing at $width',
      );
      expect(
        tester.takeException(),
        isNull,
        reason: 'overflow or exception at width $width',
      );

      final Size tableSize = tester.getSize(find.byType(ProductsTable));
      expect(
        tableSize.width,
        lessThanOrEqualTo(width),
        reason: 'table wider than the viewport at $width',
      );
    }
  });

  testWidgets('the pagination bar never appears', (tester) async {
    tester.view.devicePixelRatio = 1.0;
    tester.view.physicalSize = const Size(1600, 1000);
    addTearDown(tester.view.reset);

    await tester.pumpWidget(_harness());
    await tester.pumpAndSettle();

    expect(find.byType(AppPagination), findsNothing);
  });
}
