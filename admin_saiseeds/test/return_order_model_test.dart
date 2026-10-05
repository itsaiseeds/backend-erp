import 'package:admin_saiseeds/core/constants/app_strings.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/paginated_return_orders_model.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_edit_model.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_model.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_order_status.dart';
import 'package:admin_saiseeds/features/return_orders/data/models/return_recipe_model.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ReturnOrderStatusX', () {
    test('parses the three return statuses and rejects anything else', () {
      expect(
        ReturnOrderStatusX.fromRaw('RETURN_PENDING'),
        ReturnOrderStatus.pending,
      );
      expect(
        ReturnOrderStatusX.fromRaw('return_accepted'),
        ReturnOrderStatus.accepted,
      );
      expect(
        ReturnOrderStatusX.fromRaw('  RETURN_REJECTED  '),
        ReturnOrderStatus.rejected,
      );
      expect(
        ReturnOrderStatusX.fromRaw('DELIVERED'),
        ReturnOrderStatus.unknown,
      );
      expect(ReturnOrderStatusX.fromRaw(''), ReturnOrderStatus.unknown);
    });

    test('round-trips through rawOf', () {
      for (final status in ReturnOrderStatus.values) {
        expect(
          ReturnOrderStatusX.fromRaw(ReturnOrderStatusX.rawOf(status)),
          status,
        );
      }
    });

    test('labels every status, and unknown reads as unavailable', () {
      expect(
        ReturnOrderStatusX.labelOf(ReturnOrderStatus.pending),
        AppStrings.RETURN_ORDER_STATUS_PENDING,
      );
      expect(
        ReturnOrderStatusX.labelOf(ReturnOrderStatus.accepted),
        AppStrings.RETURN_ORDER_STATUS_ACCEPTED,
      );
      expect(
        ReturnOrderStatusX.labelOf(ReturnOrderStatus.rejected),
        AppStrings.RETURN_ORDER_STATUS_REJECTED,
      );
      expect(
        ReturnOrderStatusX.labelOf(ReturnOrderStatus.unknown),
        AppStrings.TABLE_VALUE_UNAVAILABLE,
      );
    });

    test('only a pending return can be accepted, rejected or edited', () {
      expect(ReturnOrderStatusX.canAccept(ReturnOrderStatus.pending), isTrue);
      expect(ReturnOrderStatusX.canReject(ReturnOrderStatus.pending), isTrue);
      expect(ReturnOrderStatusX.canEdit(ReturnOrderStatus.pending), isTrue);

      expect(ReturnOrderStatusX.canAccept(ReturnOrderStatus.accepted), isFalse);
      expect(ReturnOrderStatusX.canReject(ReturnOrderStatus.accepted), isFalse);
      expect(ReturnOrderStatusX.canEdit(ReturnOrderStatus.accepted), isFalse);
      expect(ReturnOrderStatusX.canEdit(ReturnOrderStatus.rejected), isFalse);
      expect(ReturnOrderStatusX.canEdit(ReturnOrderStatus.unknown), isFalse);
    });

    test('unreject and revert-accept are available only on what they undo', () {
      expect(
        ReturnOrderStatusX.canUnreject(ReturnOrderStatus.rejected),
        isTrue,
      );
      expect(
        ReturnOrderStatusX.canUnreject(ReturnOrderStatus.accepted),
        isFalse,
      );
      expect(
        ReturnOrderStatusX.canUnreject(ReturnOrderStatus.pending),
        isFalse,
      );

      expect(
        ReturnOrderStatusX.canRevertAccept(ReturnOrderStatus.accepted),
        isTrue,
      );
      expect(
        ReturnOrderStatusX.canRevertAccept(ReturnOrderStatus.rejected),
        isFalse,
      );
      expect(
        ReturnOrderStatusX.canRevertAccept(ReturnOrderStatus.pending),
        isFalse,
      );
    });
  });

  group('ReturnOrderModel.fromJson', () {
    test('reads a list row and totals its packets from the lines', () {
      final model = ReturnOrderModel.fromJson({
        'public_id': 'RET-1',
        'status': 'RETURN_PENDING',
        'return_date': '2026-02-03',
        'created_at': '2026-02-03T09:15:00Z',
        'order': {'public_id': 'ORD-9', 'status': 'DELIVERED'},
        'client': {'public_id': 'C-1', 'company_name': 'Kisan Foods'},
        'created_by': {'id': 4, 'name': 'Meera'},
        'total_kg': '7.5',
        'total_amount': '1500.00',
        'items': [
          {
            'product': {'public_id': 'P-1', 'name': 'SAI-30'},
            'packet_weight': '5.000',
            'packets': 10,
            'kg': '5.000',
            'price_per_packet': '100.00',
            'line_total': '1000.00',
          },
          {
            'product': {'public_id': 'P-2', 'name': 'SAI-31'},
            'packet_weight': '5.000',
            'packets': 5,
            'kg': '2.500',
            'price_per_packet': '100.00',
            'line_total': '500.00',
          },
        ],
      });

      expect(model.publicId, 'RET-1');
      expect(model.status, ReturnOrderStatus.pending);
      expect(model.order.publicId, 'ORD-9');
      expect(model.order.isReturnable, isTrue);
      expect(model.client.companyName, 'Kisan Foods');
      expect(model.createdByName, 'Meera');
      expect(model.totalPackets, 15);
      expect(model.totalKg, 7.5);
      expect(model.totalAmount, 1500);
    });

    test('a date-only return date is pinned to UTC midnight', () {
      final model = ReturnOrderModel.fromJson({'return_date': '2026-02-03'});

      expect(model.returnDate, DateTime.utc(2026, 2, 3));
      expect(model.returnDate!.isUtc, isTrue);
      expect(model.returnDate!.hour, 0);
    });

    test('absent actors read as empty names, not as a null crash', () {
      final model = ReturnOrderModel.fromJson({'public_id': 'RET-2'});

      expect(model.createdByName, '');
      expect(model.verifiedByName, '');
      expect(model.rejectedByName, '');
      expect(model.status, ReturnOrderStatus.unknown);
      expect(model.items, isEmpty);
      expect(model.totalPackets, 0);
      expect(model.inwardRawMaterials, isEmpty);
    });

    test('include_in_other_raw_materials is tri-state', () {
      expect(
        ReturnOrderModel.fromJson({
          'include_in_other_raw_materials': true,
        }).includeInOtherRawMaterials,
        isTrue,
      );
      expect(
        ReturnOrderModel.fromJson({
          'include_in_other_raw_materials': false,
        }).includeInOtherRawMaterials,
        isFalse,
      );
      expect(ReturnOrderModel.fromJson({}).includeInOtherRawMaterials, isNull);
    });

    test('exposes the lifecycle verbs for the status it parsed', () {
      ReturnOrderModel at(String status) =>
          ReturnOrderModel.fromJson({'status': status});

      final pending = at('RETURN_PENDING');
      expect(pending.canAccept, isTrue);
      expect(pending.canReject, isTrue);
      expect(pending.canEdit, isTrue);
      expect(pending.canUnreject, isFalse);
      expect(pending.canRevertAccept, isFalse);

      final accepted = at('RETURN_ACCEPTED');
      expect(accepted.canAccept, isFalse);
      expect(accepted.canRevertAccept, isTrue);

      final rejected = at('RETURN_REJECTED');
      expect(rejected.canAccept, isFalse);
      expect(rejected.canUnreject, isTrue);
    });
  });

  group('PaginatedReturnOrdersModel.fromJson', () {
    test('reads counts, rows and the filter/sort catalogue', () {
      final model = PaginatedReturnOrdersModel.fromJson({
        'total_count': 42,
        'total_pages': 5,
        'next_page_number': 2,
        'previous_page_number': null,
        'results': [
          {'public_id': 'RET-1', 'status': 'RETURN_PENDING'},
          {'public_id': 'RET-2', 'status': 'RETURN_ACCEPTED'},
        ],
        'available_filters': [
          {'filter': 'status', 'label': 'Status', 'kind': 'select'},
        ],
        'available_sorts': [
          {'sort': 'created_at', 'label': 'Raised on'},
        ],
      });

      expect(model.totalCount, 42);
      expect(model.totalPages, 5);
      expect(model.nextPageNumber, 2);
      expect(model.previousPageNumber, isNull);
      expect(model.results.length, 2);
      expect(model.results.first.status, ReturnOrderStatus.pending);
      expect(model.availableFilters.single.key, 'status');
      expect(model.availableSorts.single.key, 'created_at');
    });

    test('a malformed body yields an empty page rather than throwing', () {
      final model = PaginatedReturnOrdersModel.fromJson({
        'results': 'not-a-list',
        'available_filters': null,
      });

      expect(model.results, isEmpty);
      expect(model.totalCount, 0);
      expect(model.totalPages, 0);
    });
  });

  group('ReturnOrderEditRequest', () {
    final order = ReturnOrderModel.fromJson({
      'public_id': 'RET-1',
      'return_date': '2026-02-03',
      'items': [
        {
          'product': {'public_id': 'P-1', 'name': 'SAI-30'},
          'packet_weight': '5.000',
          'packets': 10,
          'price_per_packet': '100.00',
        },
      ],
    });

    test('seeds from the return as it stands', () {
      final request = ReturnOrderEditRequest.from(order);

      expect(request.returnDate, DateTime.utc(2026, 2, 3));
      expect(request.items.length, 1);
      expect(request.items.single.product.publicId, 'P-1');
      expect(request.items.single.packets, 10);
    });

    test('serialises the whole return as fixed-precision strings', () {
      final json = ReturnOrderEditRequest.from(order).toJson();

      expect(json['return_date'], '2026-02-03');
      final items = json['items'] as List;
      expect(items.length, 1);
      expect(items.first, {
        'product_public_id': 'P-1',
        'packet_weight': '5.000',
        'packets': 10,
        'price_per_packet': '100.00',
      });
    });

    test('an omitted line is a deletion, so the body carries no diff', () {
      final json = ReturnOrderEditRequest(
        items: [
          ReturnOrderItemEditModel(
            product: const ReturnProductRefModel(publicId: 'P-2'),
            packetWeight: 10,
            packets: 4,
            pricePerPacket: 12.5,
          ),
        ],
      ).toJson();

      final items = json['items'] as List;
      expect(items.length, 1);
      expect(items.first['product_public_id'], 'P-2');
      expect(items.first['packet_weight'], '10.000');
      expect(items.first['price_per_packet'], '12.50');
    });

    test('a null return date is sent as null rather than dropped', () {
      final json = ReturnOrderEditRequest(items: const []).toJson();

      expect(json['return_date'], isNull);
      expect(json['items'], isEmpty);
    });

    test('line totals follow packets and price', () {
      final line = ReturnOrderItemEditModel(
        packetWeight: 5,
        packets: 12,
        pricePerPacket: 99.5,
      );

      expect(line.kg, 60);
      expect(line.lineTotal, 1194);
      expect(line.copyWith(packets: 2).packets, 2);
      expect(line.copyWith(packets: 2).pricePerPacket, 99.5);
    });
  });

  group('Return recipe models', () {
    final recipes = ReturnOrderRecipesModel.fromJson({
      'lines': [
        {
          'product': {'public_id': 'P-1', 'name': 'SAI-30'},
          'packet_weight': '5.000',
          'packets': 10,
          'recipes': [
            {
              'public_id': 'R-1',
              'quantity': '250.000',
              'material_type': {'id': 3, 'name': 'Bag', 'unit_type': 'pcs'},
            },
            {
              'public_id': 'R-2',
              'quantity': '10.000',
              'is_deleted': true,
              'material_type': {'id': 3, 'name': 'Bag', 'unit_type': 'pcs'},
            },
            {
              'public_id': 'R-3',
              'quantity': '2.000',
              'material_type': {'id': 4, 'name': 'Label', 'unit_type': 'pcs'},
            },
          ],
        },
        {
          'product': {'public_id': 'P-2', 'name': 'SAI-31'},
          'packet_weight': '5.000',
          'packets': 5,
          'recipes': <dynamic>[],
        },
      ],
    });

    test('groups recipes per line and marks lines without any', () {
      expect(recipes.lines.length, 2);
      expect(recipes.lines.first.hasRecipes, isTrue);
      expect(recipes.lines.last.hasRecipes, isFalse);
      expect(recipes.isEmpty, isFalse);
    });

    test('a line list with no recipes anywhere is empty, not absent', () {
      expect(
        ReturnOrderRecipesModel.fromJson({
          'lines': [
            {'recipes': <dynamic>[]},
          ],
        }).isEmpty,
        isTrue,
      );
      expect(ReturnOrderRecipesModel.fromJson({}).isEmpty, isTrue);
    });

    test('quantity carries the unit type, which is per material type', () {
      final options = recipes.lines.first.recipes;
      expect(options.first.quantityLabel, '250 pcs');
    });

    test('the API keys its one-recipe-per-type rule on material type id', () {
      final options = recipes.lines.first.recipes;
      expect(options[0].materialTypeKey, options[1].materialTypeKey);
      expect(options[0].materialTypeKey, isNot(options[2].materialTypeKey));
    });

    test('a soft-deleted recipe is still offered, and says so', () {
      final deleted = recipes.lines.first.recipes[1];

      expect(deleted.isDeleted, isTrue);
      expect(deleted.publicId, 'R-2');
      expect(deleted.materialTypeName, 'Bag');
    });

    test('an absent material type does not crash the picker', () {
      final option = ReturnRecipeOptionModel.fromJson({'public_id': 'R-9'});

      expect(option.materialTypeName, '');
      expect(option.materialTypeKey, 0);
      expect(option.quantityLabel, '0 ');
    });
  });
}
