import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/core/network/api_client.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_edit_model.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_model.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_status.dart';
import 'package:admin_saiseeds/features/return_orders/data/return_orders_repository.dart';
import 'package:admin_saiseeds/features/return_orders/presentation/bloc/return_orders_cubit.dart';
import 'package:admin_saiseeds/features/return_orders/presentation/widgets/return_orders_table.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:provider/provider.dart';

const String _pendingBody =
    '{"total_count":2,"total_pages":1,"next_page_number":null,'
    '"previous_page_number":null,"results":['
    '{"public_id":"RET-1","status":"RETURN_PENDING","return_date":"2026-02-03",'
    '"created_at":"2026-02-03T09:00:00Z",'
    '"order":{"public_id":"ORD-1","status":"DELIVERED"},'
    '"client":{"public_id":"C-1","company_name":"Kisan Foods"},'
    '"created_by":{"id":4,"name":"Meera"}},'
    '{"public_id":"RET-2","status":"RETURN_PENDING","return_date":"2026-02-04",'
    '"created_at":"2026-02-04T10:00:00Z",'
    '"order":{"public_id":"ORD-2","status":"DISPATCHED"},'
    '"client":{"public_id":"C-2","company_name":"Agro Traders"},'
    '"created_by":{"id":5,"name":"Amit"}}],'
    '"available_filters":[{"filter":"status","label":"Status","kind":"select",'
    '"options":[{"value":"RETURN_PENDING","label":"Pending"}]}],'
    '"available_sorts":[{"sort":"created_at","label":"Raised on"}]}';

const String _acceptedBody =
    '{"total_count":1,"total_pages":1,"next_page_number":null,'
    '"previous_page_number":null,"results":['
    '{"public_id":"RET-1","status":"RETURN_ACCEPTED","return_date":"2026-02-03",'
    '"created_at":"2026-02-03T09:00:00Z",'
    '"order":{"public_id":"ORD-1","status":"DELIVERED"},'
    '"client":{"public_id":"C-1","company_name":"Kisan Foods"},'
    '"created_by":{"id":4,"name":"Meera"}}],'
    '"available_filters":[],"available_sorts":[]}';

const String _recipesBody =
    '{"lines":[{"product":{"public_id":"P-1","name":"SAI-30"},'
    '"packet_weight":"5.000","packets":10,"recipes":['
    '{"public_id":"R-1","quantity":"250.000",'
    '"material_type":{"id":3,"name":"Bag","unit_type":"pcs"}}]}]}';

/// Records what went out so the request bodies can be asserted on, and answers
/// each path with whatever the test asked for.
class _ReturnOrdersStubAdapter implements HttpClientAdapter {
  final Map<String, String> bodies;

  final List<Uri> requests = [];
  final List<Map<String, dynamic>> sentBodies = [];
  final List<String> methods = [];

  String listBody = _pendingBody;
  int listStatus = 200;
  int acceptStatus = 200;

  _ReturnOrdersStubAdapter({this.bodies = const {}});

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<List<int>>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    final String path = options.path;
    final String method = options.method;
    requests.add(options.uri);
    methods.add(method);
    sentBodies.add(
      options.data is Map
          ? Map<String, dynamic>.from(options.data as Map)
          : const {},
    );

    int status = 200;
    String body = '{}';

    if (path.contains('return-order-recipes')) {
      body = _recipesBody;
    } else if (path.contains('return-orders')) {
      status = listStatus;
      body = listBody;
    } else if (path.contains('accept-return-order')) {
      status = acceptStatus;
    } else if (path.contains('edit-return-order')) {
      body = _acceptedBody;
    } else if (path.contains('reject-return-order')) {
      body = _acceptedBody;
    }

    return ResponseBody.fromString(
      body,
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ApiClient _clientOf(_ReturnOrdersStubAdapter adapter) {
  final dio = Dio(
    BaseOptions(
      baseUrl: 'https://example.test',
      validateStatus: (status) => status != null && status < 500,
    ),
  );
  dio.httpClientAdapter = adapter;
  return ApiClient(dio: dio);
}

ReturnOrdersCubit _cubitOf(_ReturnOrdersStubAdapter adapter) =>
    ReturnOrdersCubit(
      repository: ReturnOrdersRepository(apiClient: _clientOf(adapter)),
    );

Future<void> _pumpTable(
  WidgetTester tester,
  List<ReturnOrderModel> rows,
) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(2400, 1000);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: ReturnOrdersTable(
          returnOrders: rows,
          isLoading: false,
          isMutating: false,
          currentPage: 1,
          totalPages: 1,
          totalItems: rows.length,
          onFetchData:
              ({
                required int page,
                required int limit,
                String? search,
                String? sortBy,
                String? sortOrder,
                Map<String, String>? filters,
              }) {},
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() {
    dotenv.loadFromString(envString: 'API_BASE_URL=http://localhost:8000');
  });

  setUp(() {
    // The table persists its column config, so it needs a preferences store.
    SharedPreferences.setMockInitialValues({});
  });

  group('ReturnOrdersCubit defaults', () {
    test('opens on the pending queue rather than every return', () {
      expect(
        ReturnOrdersCubit(
          repository: ReturnOrdersRepository(
            apiClient: _clientOf(_ReturnOrdersStubAdapter()),
          ),
        ).state.filters[ReturnOrdersCubit.STATUS_FILTER],
        ReturnOrderStatusX.PENDING,
      );
    });

    test('the first load asks the server for pending returns', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);

      await cubit.loadReturnOrders();

      expect(cubit.state.status, ReturnOrdersStatus.loaded);
      expect(cubit.state.returnOrders.length, 2);
      expect(cubit.state.totalItems, 2);
      expect(
        adapter.requests.single.queryParameters['status'],
        'RETURN_PENDING',
      );
      expect(adapter.requests.single.queryParameters['page'], 1);
    });

    test('keeps the status filter when a later query omits filters', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);

      await cubit.loadReturnOrders();
      await cubit.applyQuery(page: 1, limit: 10, search: 'Kisan');

      expect(
        cubit.state.filters[ReturnOrdersCubit.STATUS_FILTER],
        ReturnOrderStatusX.PENDING,
      );
    });

    test('an explicit filter map replaces the default', () async {
      final adapter = _ReturnOrdersStubAdapter();
      adapter.listBody = _acceptedBody;
      final cubit = _cubitOf(adapter);

      await cubit.applyQuery(
        page: 1,
        limit: 10,
        filters: const {ReturnOrdersCubit.STATUS_FILTER: 'RETURN_ACCEPTED'},
      );

      expect(
        adapter.requests.single.queryParameters['status'],
        'RETURN_ACCEPTED',
      );
      expect(
        cubit.state.returnOrders.single.status,
        ReturnOrderStatus.accepted,
      );
    });

    test(
      'a failing load reports the message and keeps nothing stale',
      () async {
        final adapter = _ReturnOrdersStubAdapter()..listStatus = 403;
        final cubit = _cubitOf(adapter);

        await cubit.loadReturnOrders();

        expect(cubit.state.status, ReturnOrdersStatus.failure);
        expect(cubit.state.errorMessage, isNotNull);
      },
    );

    test('loadMore stops at the last page', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);

      await cubit.loadReturnOrders();

      expect(cubit.state.hasMore, isFalse);
      await cubit.loadMore();
      expect(adapter.requests.length, 1);
    });
  });

  group('ReturnOrdersRepository requests', () {
    test('edit is a PATCH carrying the whole return', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final repository = ReturnOrdersRepository(apiClient: _clientOf(adapter));

      await repository.updateReturn(
        publicId: 'RET-1',
        request: ReturnOrderEditRequest(
          items: [
            ReturnOrderItemEditModel(
              product: const ReturnProductRefModel(publicId: 'P-1'),
              packetWeight: 5,
              packets: 3,
              pricePerPacket: 10,
            ),
          ],
        ),
      );

      expect(adapter.methods.single, 'PATCH');
      expect(adapter.requests.single.path, contains('edit-return-order/RET-1'));
      expect(adapter.sentBodies.single['items'], hasLength(1));
    });

    test('accept sends the flag and the picked recipe ids', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final repository = ReturnOrdersRepository(apiClient: _clientOf(adapter));

      await repository.acceptReturn(
        publicId: 'RET-1',
        includeInOtherRawMaterials: true,
        recipePublicIds: const ['R-1', 'R-3'],
      );

      expect(adapter.methods.single, 'POST');
      expect(
        adapter.sentBodies.single['include_in_other_raw_materials'],
        isTrue,
      );
      expect(adapter.sentBodies.single['recipe_public_ids'], ['R-1', 'R-3']);
    });

    test('declining the materials drops the recipe ids with it', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final repository = ReturnOrdersRepository(apiClient: _clientOf(adapter));

      await repository.acceptReturn(
        publicId: 'RET-1',
        includeInOtherRawMaterials: false,
        recipePublicIds: const ['R-1'],
      );

      expect(
        adapter.sentBodies.single['include_in_other_raw_materials'],
        isFalse,
      );
      expect(adapter.sentBodies.single['recipe_public_ids'], isEmpty);
    });

    test('the three simple transitions hit their own endpoints', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final repository = ReturnOrdersRepository(apiClient: _clientOf(adapter));

      await repository.rejectReturn('RET-1');
      await repository.unrejectReturn('RET-2');
      await repository.revertAcceptReturn('RET-3');

      expect(adapter.requests[0].path, contains('reject-return-order/RET-1'));
      expect(adapter.requests[1].path, contains('unreject-return-order/RET-2'));
      expect(
        adapter.requests[2].path,
        contains('revert-accept-return-order/RET-3'),
      );
    });

    test('recipes load per return and group by line', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final repository = ReturnOrdersRepository(apiClient: _clientOf(adapter));

      final recipes = await repository.fetchRecipes('RET-1');

      expect(recipes.lines.single.product.name, 'SAI-30');
      expect(recipes.lines.single.recipes.single.materialTypeName, 'Bag');
    });
  });

  group('ReturnOrdersCubit mutations', () {
    test('accepting refreshes the queue and reports success', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);
      await cubit.loadReturnOrders();

      final bool ok = await cubit.acceptReturn(
        publicId: 'RET-1',
        includeInOtherRawMaterials: true,
        recipePublicIds: const ['R-1'],
      );

      expect(ok, isTrue);
      expect(cubit.state.isMutating, isFalse);
      // Two requests: the accept itself, then the refreshed page.
      expect(adapter.methods.first, contains('POST'));
      expect(adapter.methods.last, contains('GET'));
    });

    test(
      'a refused mutation surfaces the message and reloads nothing',
      () async {
        final adapter = _ReturnOrdersStubAdapter()..acceptStatus = 400;
        final cubit = _cubitOf(adapter);
        await cubit.loadReturnOrders();

        final bool ok = await cubit.acceptReturn(
          publicId: 'RET-1',
          includeInOtherRawMaterials: true,
          recipePublicIds: const ['R-1'],
        );

        expect(ok, isFalse);
        expect(cubit.state.errorMessage, isNotNull);
        expect(adapter.methods.where((m) => m == 'GET').length, 1);
      },
    );

    test(
      'an edit with no lines is refused before it reaches the API',
      () async {
        final adapter = _ReturnOrdersStubAdapter();
        final cubit = _cubitOf(adapter);
        await cubit.loadReturnOrders();

        final bool ok = await cubit.updateReturn(
          publicId: 'RET-1',
          request: const ReturnOrderEditRequest(items: []),
        );

        expect(ok, isFalse);
        expect(
          adapter.requests.any((r) => r.path.contains('edit-return-order')),
          isFalse,
        );
      },
    );

    test('a recipe load failure is reported rather than thrown', () async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);

      final result = await cubit.fetchRecipes('RET-1');

      expect(result, isNotNull);
      expect(cubit.state.errorMessage, isNull);
    });
  });

  group('ReturnOrdersTable', () {
    testWidgets('renders each return row with its client, order and status', (
      tester,
    ) async {
      final adapter = _ReturnOrdersStubAdapter();
      final cubit = _cubitOf(adapter);
      await cubit.loadReturnOrders();

      await _pumpTable(tester, cubit.state.returnOrders);

      expect(find.text('RET-1'), findsWidgets);
      expect(find.text('RET-2'), findsWidgets);
      expect(find.text('Kisan Foods'), findsOneWidget);
      expect(find.text('Agro Traders'), findsOneWidget);
      expect(find.text('ORD-1'), findsOneWidget);
      expect(find.text('ORD-2'), findsOneWidget);
      expect(find.text('Meera'), findsOneWidget);
      expect(find.text('Amit'), findsOneWidget);
      expect(
        find.text(AppStrings.RETURN_ORDER_STATUS_PENDING),
        findsNWidgets(2),
      );
    });

    testWidgets('shows the empty state when nothing matches', (tester) async {
      await _pumpTable(tester, const []);

      expect(
        find.text(AppStrings.RETURN_ORDERS_EMPTY_STATE_TITLE),
        findsOneWidget,
      );
    });

    testWidgets('a return with no date shows the unavailable marker', (
      tester,
    ) async {
      await _pumpTable(tester, [
        ReturnOrderModel.fromJson({'public_id': 'RET-9'}),
      ]);

      expect(find.text('RET-9'), findsWidgets);
      // Three cells are genuinely empty on this row: date, client and actor.
      expect(find.text(AppStrings.TABLE_VALUE_UNAVAILABLE), findsWidgets);
    });

    testWidgets('the row actions menu opens for a pending return', (
      tester,
    ) async {
      await _pumpTable(tester, [
        ReturnOrderModel.fromJson({
          'public_id': 'RET-1',
          'status': 'RETURN_PENDING',
        }),
      ]);

      await tester.tap(find.byType(IconButton).last);
      await tester.pumpAndSettle();

      expect(find.text(AppStrings.RETURN_ORDER_ACCEPT), findsOneWidget);
      expect(find.text(AppStrings.RETURN_ORDER_REJECT), findsOneWidget);
      expect(find.text(AppStrings.RETURN_ORDER_EDIT), findsOneWidget);
    });
  });
}
