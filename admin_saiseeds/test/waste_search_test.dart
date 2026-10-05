import 'package:flutter_test/flutter_test.dart';
import 'package:admin_saiseeds/features/waste_management/data/models/waste_model.dart';
import 'package:admin_saiseeds/features/waste_management/presentation/bloc/waste_management_cubit.dart';

const List<WasteModel> _wastes = [
  WasteModel(
    publicId: 'WS-0001',
    product: WasteProductRef(publicId: 'PD-1', name: 'Arabica Robusta'),
    quantityKg: '12.500',
    reason: 'Spoiled in transit',
    createdAt: '2026-01-03T00:00:00Z',
  ),
  WasteModel(
    publicId: 'WS-0002',
    product: WasteProductRef(publicId: 'PD-2', name: 'Maso Danco'),
    quantityKg: '4.000',
    reason: 'Water damage',
    createdAt: '2026-01-01T00:00:00Z',
  ),
  WasteModel(
    publicId: 'WS-0003',
    quantityKg: '7.250',
    createdAt: '2026-01-02T00:00:00Z',
  ),
];

void main() {
  group('waste search', () {
    test('an empty query matches every row', () {
      expect(_wastes.where((w) => w.matchesSearch('')).length, 3);
      expect(_wastes.where((w) => w.matchesSearch('   ')).length, 3);
    });

    test('matches on product name, case-insensitively', () {
      expect(
        _wastes.where((w) => w.matchesSearch('robusta')).single.publicId,
        'WS-0001',
      );
      expect(_wastes.where((w) => w.matchesSearch('MASO')).length, 1);
    });

    test('matches on reason', () {
      expect(
        _wastes.where((w) => w.matchesSearch('water')).single.publicId,
        'WS-0002',
      );
    });

    test('matches on quantity and reference', () {
      expect(
        _wastes.where((w) => w.matchesSearch('7.25')).single.publicId,
        'WS-0003',
      );
      expect(
        _wastes.where((w) => w.matchesSearch('ws-0002')).single.publicId,
        'WS-0002',
      );
    });

    test('an unmatched query matches nothing', () {
      expect(_wastes.where((w) => w.matchesSearch('zzzz')).isEmpty, isTrue);
    });
  });

  group('waste state filtering', () {
    WasteManagementState stateWith(String search) =>
        WasteManagementState(wastes: _wastes, search: search);

    test('visibleWastes returns all rows when no search is active', () {
      expect(stateWith('').visibleWastes.length, 3);
      expect(stateWith('   ').visibleWastes.length, 3);
    });

    test('visibleWastes narrows rows when a search is active', () {
      expect(stateWith('robusta').visibleWastes.single.publicId, 'WS-0001');
      expect(stateWith('robusta').hasSearch, isTrue);
    });

    test('isEmptySource is false once a search narrows to nothing', () {
      final state = stateWith('zzzz');

      expect(state.visibleWastes, isEmpty);
      expect(state.isEmptySource, isFalse);
    });

    test('isEmptySource is true only with no search and no filters', () {
      expect(const WasteManagementState().isEmptySource, isTrue);
      expect(
        WasteManagementState(filters: const {'product': 'PD-1'}).isEmptySource,
        isFalse,
      );
    });
  });
}
