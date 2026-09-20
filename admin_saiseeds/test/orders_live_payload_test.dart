import 'dart:convert';

import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/data/models/paginated_orders_model.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_detail_dialog.dart';
import 'package:admin_saiseeds/features/orders/presentation/widgets/order_status_badge.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const String _liveResponse = r'''
{
  "total_count": 1,
  "total_pages": 1,
  "next_page_number": null,
  "previous_page_number": null,
  "results": [
    {
      "public_id": "ORD-X1Q5NK84WGV2",
      "created_at": "2026-09-14T18:02:05.274437+00:00",
      "status": "BOOKED",
      "client": {"public_id": "C-BREB4DIUEQ6Y", "company_name": "sgdg"},
      "delivery_address": "eywy, Rajkot, Gujarat, India",
      "city": {"id": 3, "name": "Rajkot"},
      "expected_delivery_date": "2026-09-15",
      "dispatch_mode": "PRIVATE",
      "total_amount": "9800.00",
      "total_packets": 60,
      "item_count": 2,
      "packagings": [
        {
          "negotiated_selling_price": "4800.00",
          "public_id": "PP-U4UYPFOF08NZ",
          "product": {
            "public_id": "P-I34V7RI1JPUH",
            "name": "SAI-33",
            "image_url": ""
          },
          "packet_weight": "1.000",
          "packets": 40,
          "total_weight": "40.000",
          "selling_price": "4800.00",
          "quantity": 1
        },
        {
          "negotiated_selling_price": "5000.00",
          "public_id": "PP-5SVE39LY2XEI",
          "product": {
            "public_id": "P-NQ8N4LF7MJYQ",
            "name": "SAI-3353",
            "image_url": ""
          },
          "packet_weight": "1.500",
          "packets": 20,
          "total_weight": "30.000",
          "selling_price": "5000.00",
          "quantity": 1
        }
      ],
      "created_by": "Sales Person User",
      "verified_by": null,
      "client_created_by": "Sales Person User",
      "transport_agency": null
    }
  ],
  "available_filters": [
    {
      "filter": "created_by",
      "label": "Sales Person",
      "kind": "select",
      "description": "User id(s).",
      "options": [{"value": 3, "label": "Sales Person User"}]
    },
    {
      "filter": "status",
      "label": "Status",
      "kind": "select",
      "description": "Order lifecycle status.",
      "options": [{"value": "BOOKED", "label": "Booked"}]
    }
  ],
  "available_sorts": [
    {"sort": "created_at", "label": "Created", "description": "Newest first."},
    {"sort": "price", "label": "Price", "description": "Cheapest first."}
  ]
}
''';

PaginatedOrdersModel _page() => PaginatedOrdersModel.fromJson(
  Map<String, dynamic>.from(jsonDecode(_liveResponse) as Map),
);

OrderModel _order() => _page().results.single;

Future<void> _openDetail(WidgetTester tester, {int step = 0}) async {
  tester.view.devicePixelRatio = 1.0;
  tester.view.physicalSize = const Size(1400, 1100);
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: OrderDetailDialog(order: _order())),
    ),
  );
  await tester.pumpAndSettle();

  for (int i = 0; i < step; i++) {
    await tester.tap(find.text(AppStrings.STEP_NEXT));
    await tester.pumpAndSettle();
  }
}

void main() {
  group('the live order payload', () {
    test('parses into a usable card', () {
      final OrderModel order = _order();

      expect(order.publicId, 'ORD-X1Q5NK84WGV2');
      expect(order.client.name, 'sgdg');
      expect(order.status, OrderStatus.booked);
      expect(order.totalAmount, 9800);
      expect(order.totalPackets, 60);
      expect(order.itemCount, 2);
      expect(order.createdBy, 'Sales Person User');
    });

    test('a null verified_by and agency do not break the model', () {
      final OrderModel order = _order();

      expect(order.verifiedBy, '');
      expect(order.transportAgency, isNull);
      expect(order.agencyName, '');
      expect(order.isAgencyDispatch, isFalse);
    });

    test('fractional packet weights survive the decimal strings', () {
      final OrderPackagingModel second = _order().packagings.last;

      expect(second.packetWeight, 1.5);
      expect(second.packetSummary, '20 x 1.5 kg');
      expect(second.totalWeightSummary, '30 Kg');
    });

    test('list price equal to negotiated is not flagged as a discount', () {
      for (final OrderPackagingModel line in _order().packagings) {
        expect(line.isNegotiated, isFalse);
      }
    });

    test('the line totals add up to the order total', () {
      final OrderModel order = _order();
      final num sum = order.packagings.fold<num>(
        0,
        (total, line) => total + line.lineTotal,
      );

      expect(sum, order.totalAmount);
    });

    test('integer filter option values are usable as query strings', () {
      final page = _page();
      final options = page.availableFilters.first.options;

      expect(options.single.value, '3');
      expect(options.single.label, 'Sales Person User');
    });

    test('backend labels drive the filter and sort titles', () {
      final page = _page();

      expect(page.availableFilters.first.displayLabel, 'Sales Person');
      expect(page.availableSorts.last.displayLabel, 'Price');
    });
  });

  group('the detail dialog on live data', () {
    testWidgets('closes on the summary with the totals', (tester) async {
      await _openDetail(tester, step: 2);

      expect(find.text('sgdg'), findsOneWidget);
      expect(find.text('ORD-X1Q5NK84WGV2'), findsOneWidget);
      expect(find.byType(OrderStatusBadge), findsOneWidget);
      expect(find.textContaining('9,800'), findsOneWidget);
      expect(find.text('60'), findsOneWidget);
    });

    testWidgets('an unverified order says so rather than showing a dash', (
      tester,
    ) async {
      await _openDetail(tester);

      expect(find.text(AppStrings.ORDER_AWAITING_VERIFICATION), findsOneWidget);
    });

    testWidgets('the items step is never empty when the order has lines', (
      tester,
    ) async {
      await _openDetail(tester, step: 1);

      // Refetching from the detail endpoint returned lines under "items",
      // not "packagings", which emptied this step on a real order.
      expect(find.text(AppStrings.ORDER_NO_ITEMS), findsNothing);
    });

    testWidgets('the summary carries the totals once, not twice', (
      tester,
    ) async {
      await _openDetail(tester, step: 2);

      expect(find.textContaining('9,800'), findsOneWidget);
      expect(find.text('60'), findsOneWidget);
      expect(find.text('sgdg'), findsOneWidget);
    });

    testWidgets('the items step lists every product with its pack size', (
      tester,
    ) async {
      await _openDetail(tester, step: 1);

      expect(find.text('SAI-33'), findsOneWidget);
      expect(find.text('SAI-3353'), findsOneWidget);
      expect(find.textContaining('40 x 1 kg'), findsOneWidget);
      expect(find.textContaining('20 x 1.5 kg'), findsOneWidget);
    });

    testWidgets('a product with no image falls back to a placeholder', (
      tester,
    ) async {
      await _openDetail(tester, step: 1);

      // Live products carry an empty image_url, so Image.network must not run.
      expect(find.byType(Image), findsNothing);
      // Two thumbnails, plus the section heading icon.
      expect(find.byIcon(Icons.inventory_2_outlined), findsNWidgets(3));
    });

    testWidgets('the delivery step names a private dispatch', (tester) async {
      await _openDetail(tester, step: 2);

      expect(find.text('eywy, Rajkot, Gujarat, India'), findsOneWidget);
      expect(find.text('Rajkot'), findsOneWidget);
      expect(find.text(AppStrings.ORDER_DISPATCH_PRIVATE), findsNWidgets(2));
    });
  });
}
