import 'dart:convert';

import 'package:admin_saiseeds/features/orders/data/models/order_model.dart';
import 'package:admin_saiseeds/features/orders/data/models/order_status.dart';
import 'package:admin_saiseeds/features/orders/data/models/paginated_orders_model.dart';
import 'package:flutter_test/flutter_test.dart';

const String _page = '''
{
  "total_count": 1,
  "total_pages": 1,
  "next_page_number": null,
  "previous_page_number": null,
  "results": [
    {
      "public_id": "ORD-E79QA0E2OIHF",
      "created_at": "2026-09-13T19:26:35.134Z",
      "status": "CONFIRMED",
      "client": {"public_id": "C-1", "company_name": "Dharati Agro"},
      "client_created_by": "Asha Sales",
      "created_by": "Ravi Sales",
      "verified_by": "Priya Admin",
      "delivery_address": "Plot 4, Ring Road, Rajkot",
      "city": {"id": 7, "name": "Rajkot"},
      "transport_agency": {"id": 3, "name": "Speedy Roadways"},
      "dispatch_mode": "AGENCY",
      "expected_delivery_date": "2026-09-20",
      "total_amount": "35000.00",
      "total_packets": 120,
      "item_count": 2,
      "packagings": [
        {
          "public_id": "PP-1",
          "negotiated_selling_price": "2400.00",
          "product": {
            "public_id": "P-1",
            "name": "SAI-30",
            "image_url": "/media/products/sai30.jpg"
          },
          "packet_weight": "2.00",
          "packets": 40,
          "total_weight": "80.00",
          "selling_price": "2500.00",
          "quantity": 2
        },
        {
          "public_id": "PP-2",
          "product": {"public_id": "P-2", "name": "SAI-31", "image_url": ""},
          "packet_weight": "1.00",
          "packets": 30,
          "total_weight": "30.00",
          "selling_price": "1200.00",
          "quantity": 1
        }
      ]
    }
  ],
  "available_filters": [
    {
      "filter": "status",
      "label": "Status",
      "kind": "select",
      "description": "",
      "params": [],
      "options": [{"value": "BOOKED", "label": "Booked"}]
    }
  ],
  "available_sorts": [
    {"sort": "created_at", "label": "Created", "description": ""}
  ]
}
''';

OrderModel _order() {
  return PaginatedOrdersModel.fromJson(
    Map<String, dynamic>.from(jsonDecode(_page) as Map),
  ).results.single;
}

void main() {
  group('order parsing', () {
    test('reads the admin card fields', () {
      final OrderModel order = _order();

      expect(order.publicId, 'ORD-E79QA0E2OIHF');
      expect(order.client.name, 'Dharati Agro');
      expect(order.createdBy, 'Ravi Sales');
      expect(order.clientCreatedBy, 'Asha Sales');
      expect(order.verifiedBy, 'Priya Admin');
      expect(order.cityName, 'Rajkot');
      expect(order.agencyName, 'Speedy Roadways');
      expect(order.isAgencyDispatch, isTrue);
    });

    test('decimal strings become numbers', () {
      final OrderModel order = _order();

      expect(order.totalAmount, 35000);
      expect(order.packagings.first.packetWeight, 2);
      expect(order.packagings.first.sellingPrice, 2500);
      expect(order.packagings.first.negotiatedSellingPrice, 2400);
    });

    test('a line total uses the negotiated price when there is one', () {
      final OrderPackagingModel line = _order().packagings.first;

      expect(line.effectivePrice, 2400);
      expect(line.lineTotal, 4800);
      expect(line.isNegotiated, isTrue);
    });

    test('a line with no negotiated price falls back to list price', () {
      final OrderPackagingModel line = _order().packagings.last;

      expect(line.effectivePrice, 1200);
      expect(line.lineTotal, 1200);
      expect(line.isNegotiated, isFalse);
    });

    test('bags are counted across lines', () {
      expect(_order().bagCount, 3);
    });

    test('a null city and agency do not crash the card', () {
      final OrderModel order = OrderModel.fromJson(const {
        'public_id': 'ORD-1',
        'city': null,
        'transport_agency': null,
        'dispatch_mode': 'PRIVATE',
      });

      expect(order.cityName, '');
      expect(order.agencyName, '');
      expect(order.isAgencyDispatch, isFalse);
    });

    test('the envelope carries filters and sorts', () {
      final PaginatedOrdersModel page = PaginatedOrdersModel.fromJson(
        Map<String, dynamic>.from(jsonDecode(_page) as Map),
      );

      expect(page.totalCount, 1);
      expect(page.availableFilters.single.key, 'status');
      expect(page.availableSorts.single.key, 'created_at');
    });
  });

  group('order actions follow the backend transition rules', () {
    test('verify is allowed from booked, under review and on hold', () {
      expect(OrderStatusX.canVerify(OrderStatus.booked), isTrue);
      expect(OrderStatusX.canVerify(OrderStatus.underReview), isTrue);
      expect(OrderStatusX.canVerify(OrderStatus.onHold), isTrue);
    });

    test('a confirmed order cannot be verified twice', () {
      expect(OrderStatusX.canVerify(OrderStatus.confirmed), isFalse);
    });

    test('a rejected order is terminal for every action', () {
      expect(OrderStatusX.canVerify(OrderStatus.rejected), isFalse);
      expect(OrderStatusX.canUnverify(OrderStatus.rejected), isFalse);
      expect(OrderStatusX.canHold(OrderStatus.rejected), isFalse);
      expect(OrderStatusX.canReject(OrderStatus.rejected), isFalse);
    });

    test('unverify is only allowed from confirmed', () {
      expect(OrderStatusX.canUnverify(OrderStatus.confirmed), isTrue);
      for (final OrderStatus status in OrderStatus.values) {
        if (status == OrderStatus.confirmed) continue;
        expect(OrderStatusX.canUnverify(status), isFalse);
      }
    });

    test('hold is allowed before dispatch only', () {
      expect(OrderStatusX.canHold(OrderStatus.booked), isTrue);
      expect(OrderStatusX.canHold(OrderStatus.underReview), isTrue);
      expect(OrderStatusX.canHold(OrderStatus.confirmed), isTrue);
      expect(OrderStatusX.canHold(OrderStatus.dispatched), isFalse);
      expect(OrderStatusX.canHold(OrderStatus.delivered), isFalse);
    });

    test('a held order cannot be held again', () {
      expect(OrderStatusX.canHold(OrderStatus.onHold), isFalse);
    });

    test('reject is hold plus on hold, still never after dispatch', () {
      expect(OrderStatusX.canReject(OrderStatus.booked), isTrue);
      expect(OrderStatusX.canReject(OrderStatus.underReview), isTrue);
      expect(OrderStatusX.canReject(OrderStatus.confirmed), isTrue);
      expect(OrderStatusX.canReject(OrderStatus.onHold), isTrue);
      expect(OrderStatusX.canReject(OrderStatus.dispatched), isFalse);
      expect(OrderStatusX.canReject(OrderStatus.delivered), isFalse);
    });

    test('editing stops once the goods have shipped', () {
      expect(OrderStatusX.canEdit(OrderStatus.confirmed), isTrue);
      expect(OrderStatusX.canEdit(OrderStatus.dispatched), isFalse);
      expect(OrderStatusX.canEdit(OrderStatus.delivered), isFalse);
    });

    test('an unknown status offers no action at all', () {
      expect(OrderStatusX.canVerify(OrderStatus.unknown), isFalse);
      expect(OrderStatusX.canUnverify(OrderStatus.unknown), isFalse);
      expect(OrderStatusX.canHold(OrderStatus.unknown), isFalse);
      expect(OrderStatusX.canReject(OrderStatus.unknown), isFalse);
    });

    test('the parsed order exposes the same rules', () {
      final OrderModel confirmed = _order();

      expect(confirmed.status, OrderStatus.confirmed);
      expect(confirmed.canVerify, isFalse);
      expect(confirmed.canUnverify, isTrue);
      expect(confirmed.canHold, isTrue);
      expect(confirmed.canReject, isTrue);
    });
  });

  group('order status codes', () {
    test('every backend code round-trips', () {
      for (final OrderStatus status in OrderStatus.values) {
        if (status == OrderStatus.unknown) continue;
        final String raw = OrderStatusX.rawOf(status);
        expect(OrderStatusX.fromRaw(raw), status);
      }
    });

    test('an unknown code does not throw', () {
      expect(OrderStatusX.fromRaw('SOMETHING_NEW'), OrderStatus.unknown);
      expect(OrderStatusX.fromRaw(''), OrderStatus.unknown);
    });
  });

  group('edit payload', () {
    test('a line sends the packaging id, quantity and agreed price', () {
      final Map<String, dynamic> json = _order().packagings.first.toEditJson();

      expect(json['product_packaging_public_id'], 'PP-1');
      expect(json['quantity'], 2);
      expect(json['negotiated_selling_price'], '2400.00');
    });

    test('copyWith changes quantity without losing the rest', () {
      final OrderPackagingModel line = _order().packagings.first.copyWith(
        quantity: 5,
      );

      expect(line.quantity, 5);
      expect(line.publicId, 'PP-1');
      expect(line.negotiatedSellingPrice, 2400);
      expect(line.lineTotal, 12000);
    });
  });
}
